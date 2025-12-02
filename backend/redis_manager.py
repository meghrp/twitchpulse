from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from redis.asyncio import Redis

from .config import get_settings

settings = get_settings()


class RedisManager:
    """Encapsulates all Redis interactions for chat sessions."""

    def __init__(self) -> None:
        redis_kwargs = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        # Only pass the ssl flag when the instance actually needs TLS. Older redis-py
        # releases (including the wheel bundled with python:slim) choke on ssl=None.
        if settings.redis_use_ssl:
            redis_kwargs["ssl"] = True

        self._client = Redis.from_url(
            settings.redis_url,
            **redis_kwargs,
        )

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    async def initialize_session(self, session_id: str, channel: str, duration: int) -> None:
        await self.purge_session(session_id)

        now = datetime.now(timezone.utc).isoformat()
        info_key = self._info_key(session_id)
        timeline_key = self._timeline_key(session_id)

        pipe = self._client.pipeline()
        pipe.hset(
            info_key,
            mapping={
                "channel": channel.lower(),
                "duration": duration,
                "status": "active",
                "started_at": now,
            },
        )
        pipe.expire(info_key, settings.session_ttl_seconds)
        pipe.set(self._message_count_key(session_id), 0)
        pipe.expire(self._message_count_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._chatters_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._emotes_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._emote_names_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._emote_images_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._sentiment_key(session_id), settings.session_ttl_seconds)
        pipe.expire(timeline_key, settings.session_ttl_seconds)
        await pipe.execute()

    async def purge_session(self, session_id: str) -> None:
        keys = [
            self._info_key(session_id),
            self._chatters_key(session_id),
            self._emotes_key(session_id),
            self._emote_names_key(session_id),
            self._sentiment_key(session_id),
            self._message_count_key(session_id),
            self._timeline_key(session_id),
            self._emote_images_key(session_id),
        ]
        if keys:
            await self._client.delete(*keys)

    async def close_session(self, session_id: str, status: str = "complete") -> None:
        info_key = self._info_key(session_id)
        await self._client.hset(info_key, mapping={"status": status, "ended_at": self._now()})

    async def increment_message_count(self, session_id: str, amount: int = 1) -> int:
        key = self._message_count_key(session_id)
        new_value = await self._client.incrby(key, amount)
        await self._client.expire(key, settings.session_ttl_seconds)
        return new_value

    async def increment_chatter(self, session_id: str, username: str) -> None:
        key = self._chatters_key(session_id)
        await self._client.zincrby(key, 1, username.lower())
        await self._client.expire(key, settings.session_ttl_seconds)

    async def increment_emotes(self, session_id: str, emotes: List[Tuple[str, str]]) -> None:
        if not emotes:
            return
        pipe = self._client.pipeline()
        for emote_id, emote_name in emotes:
            pipe.hincrby(self._emotes_key(session_id), emote_id, 1)
            pipe.hsetnx(self._emote_names_key(session_id), emote_id, emote_name)
        pipe.expire(self._emotes_key(session_id), settings.session_ttl_seconds)
        pipe.expire(self._emote_names_key(session_id), settings.session_ttl_seconds)
        await pipe.execute()

    async def set_emote_image(self, session_id: str, emote_id: str, image_url: str) -> None:
        if not image_url:
            return
        key = self._emote_images_key(session_id)
        await self._client.hset(key, emote_id, image_url)
        await self._client.expire(key, settings.session_ttl_seconds)

    async def update_sentiment(self, session_id: str, label: str, score: float) -> None:
        sent_key = self._sentiment_key(session_id)
        pipe = self._client.pipeline()
        pipe.hincrby(sent_key, label, 1)
        pipe.hincrbyfloat(sent_key, f"{label}_sum", float(score))
        pipe.expire(sent_key, settings.session_ttl_seconds)
        await pipe.execute()

    async def append_timeline(self, session_id: str, timestamp: int) -> None:
        key = self._timeline_key(session_id)
        pipe = self._client.pipeline()
        pipe.rpush(key, str(timestamp))
        pipe.ltrim(key, -1200, -1)  # keep roughly last 20 minutes
        pipe.expire(key, settings.session_ttl_seconds)
        await pipe.execute()

    async def get_stats(self, session_id: str, top_n: int = 10) -> Dict[str, Any]:
        info_key = self._info_key(session_id)
        timeline_key = self._timeline_key(session_id)
        message_key = self._message_count_key(session_id)

        info, timeline, total_messages = await asyncio.gather(
            self._client.hgetall(info_key),
            self._client.lrange(timeline_key, 0, -1),
            self._client.get(message_key),
        )

        total_messages = int(total_messages or 0)
        chatter_count, top_chatters = await asyncio.gather(
            self._client.zcard(self._chatters_key(session_id)),
            self._client.zrevrange(self._chatters_key(session_id), 0, top_n - 1, withscores=True),
        )

        emote_counts = await self._client.hgetall(self._emotes_key(session_id))
        emote_names = await self._client.hgetall(self._emote_names_key(session_id))
        emote_images = await self._client.hgetall(self._emote_images_key(session_id))
        sentiment = await self._client.hgetall(self._sentiment_key(session_id))

        top_emotes = self._format_top_emotes(emote_counts, emote_names, emote_images, top_n)
        sentiment_summary = self._format_sentiment(sentiment)

        minutes_window_count = self._count_recent(timeline, window_seconds=60)
        messages_per_minute = minutes_window_count

        return {
            "sessionId": session_id,
            "session": info,
            "messageCount": total_messages,
            "chatterCount": chatter_count,
            "messagesPerMinute": messages_per_minute,
            "topChatters": [{"username": name, "count": int(score)} for name, score in top_chatters],
            "topEmotes": top_emotes,
            "sentiment": sentiment_summary,
        }

    def _format_top_emotes(
        self, counts: Dict[str, str], names: Dict[str, str], images: Dict[str, str], limit: int
    ) -> List[Dict[str, Any]]:
        scored = [(emote_id, int(count)) for emote_id, count in counts.items()]
        scored.sort(key=lambda item: item[1], reverse=True)
        result = []
        for emote_id, count in scored[:limit]:
            result.append(
                {
                    "id": emote_id,
                    "name": names.get(emote_id, emote_id),
                    "count": count,
                    "imageUrl": images.get(emote_id) or self._emote_cdn_url(emote_id),
                }
            )
        return result

    def _format_sentiment(self, sentiment: Dict[str, str]) -> Dict[str, Any]:
        positive = int(sentiment.get("positive", 0))
        negative = int(sentiment.get("negative", 0))
        neutral = int(sentiment.get("neutral", 0))
        total = max(positive + negative + neutral, 1)

        return {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positivePct": round((positive / total) * 100, 2),
            "negativePct": round((negative / total) * 100, 2),
            "neutralPct": round((neutral / total) * 100, 2),
        }

    def _count_recent(self, entries: List[str], window_seconds: int) -> int:
        if not entries:
            return 0
        cutoff = int(time.time()) - window_seconds
        return sum(1 for raw_ts in entries if raw_ts and int(raw_ts) >= cutoff)

    @staticmethod
    def _emote_cdn_url(emote_id: str, theme: str = "dark", scale: str = "2.0") -> str:
        return f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/{theme}/{scale}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _info_key(self, session_id: str) -> str:
        return f"session:{session_id}:info"

    def _chatters_key(self, session_id: str) -> str:
        return f"session:{session_id}:chatters"

    def _emotes_key(self, session_id: str) -> str:
        return f"session:{session_id}:emotes"

    def _emote_names_key(self, session_id: str) -> str:
        return f"session:{session_id}:emote_names"

    def _emote_images_key(self, session_id: str) -> str:
        return f"session:{session_id}:emote_images"

    def _sentiment_key(self, session_id: str) -> str:
        return f"session:{session_id}:sentiment"

    def _message_count_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    def _timeline_key(self, session_id: str) -> str:
        return f"session:{session_id}:timeline"

