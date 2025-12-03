from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SEVENTV_API = "https://7tv.io/v3"
TOKEN_REGEX = re.compile(r"[A-Za-z0-9_]+")


@dataclass(slots=True)
class SevenTVEmote:
    key: str  # prefixed id (e.g., 7tv:<id>)
    name: str
    image_url: str


class SevenTVService:
    """Fetches and caches 7TV emotes for Twitch channels."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)
        self._global_emotes: Dict[str, SevenTVEmote] = {}
        self._session_emotes: Dict[str, Dict[str, SevenTVEmote]] = {}
        self._lock = asyncio.Lock()

    async def warm_globals(self) -> None:
        async with self._lock:
            if self._global_emotes:
                return
            try:
                resp = await self._client.get(f"{SEVENTV_API}/emote-sets/global")
                resp.raise_for_status()
                data = resp.json()
                emotes = self._extract_emotes(data.get("emotes", []))
                self._global_emotes = {emote.name.lower(): emote for emote in emotes}
                logger.info("Cached %s global 7TV emotes", len(self._global_emotes))
            except httpx.HTTPError as exc:
                logger.warning("Unable to warm 7TV global emotes: %s", exc)

    async def load_session(self, session_id: str, channel_login: str) -> None:
        await self.warm_globals()
        emotes = {}
        emotes.update(self._global_emotes)
        channel_emotes = await self._fetch_channel_emotes(channel_login)
        emotes.update({emote.name.lower(): emote for emote in channel_emotes})
        self._session_emotes[session_id] = emotes
        logger.info("Loaded %s 7TV emotes for #%s", len(emotes), channel_login)

    async def drop_session(self, session_id: str) -> None:
        self._session_emotes.pop(session_id, None)

    def match_message(self, session_id: str, content: str) -> List[SevenTVEmote]:
        lookup = self._session_emotes.get(session_id)
        if not lookup or not content:
            return []
        matches: List[SevenTVEmote] = []
        seen: set[str] = set()
        for token in TOKEN_REGEX.findall(content):
            key = token.lower()
            emote = lookup.get(key)
            if emote and emote.key not in seen:
                matches.append(emote)
                seen.add(emote.key)
        return matches

    async def close(self) -> None:
        await self._client.aclose()

    async def _fetch_channel_emotes(self, channel_login: str) -> List[SevenTVEmote]:
        url = f"{SEVENTV_API}/users/twitch/{channel_login.lower()}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            emote_set = data.get("emote_set", {})
            return self._extract_emotes(emote_set.get("emotes", []))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("No 7TV profile for channel %s", channel_login)
            else:
                logger.warning("7TV channel fetch failed for %s: %s", channel_login, exc)
        except httpx.HTTPError as exc:
            logger.warning("7TV channel fetch error for %s: %s", channel_login, exc)
        return []

    def _extract_emotes(self, entries: List[Dict]) -> List[SevenTVEmote]:
        emotes: List[SevenTVEmote] = []
        for entry in entries or []:
            data = entry.get("data") or {}
            emote_id = data.get("id")
            name = data.get("name")
            host = data.get("host") or {}
            files = host.get("files") or []
            image_url = self._select_image_url(host.get("base_url"), files)
            if emote_id and name and image_url:
                emotes.append(
                    SevenTVEmote(
                        key=f"7tv:{emote_id}",
                        name=name,
                        image_url=image_url,
                    )
                )
        return emotes

    @staticmethod
    def _select_image_url(base_url: Optional[str], files: List[Dict]) -> Optional[str]:
        if not base_url or not files:
            return None
        # prefer 2x static image
        candidates = sorted(files, key=lambda f: f.get("scale", 0))
        for file in candidates:
            if file.get("format") != "AVIF":  # prefer widely supported formats
                return f"{base_url}/{file.get('name')}"
        first = candidates[0]
        return f"{base_url}/{first.get('name')}" if first else None

