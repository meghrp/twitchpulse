from __future__ import annotations

import asyncio
import logging

from twitchio import Message
from twitchio.ext import commands

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TwitchChatClient(commands.Bot):
    """Thin wrapper around TwitchIO Bot that pushes messages into an asyncio queue."""

    def __init__(self, channel: str, message_queue: asyncio.Queue, sample_rate: int = 1) -> None:
        if not settings.twitch_chat_oauth_token:
            raise RuntimeError("TWITCH_CHAT_OAUTH_TOKEN is required to connect to Twitch chat.")

        super().__init__(
            token=settings.twitch_chat_oauth_token,
            prefix="!",
            initial_channels=[channel.lower()],
            nick=settings.twitch_bot_username,
        )
        self._queue = message_queue
        self._sample_rate = max(sample_rate, 1)
        self._counter = 0
        self._channel = channel.lower()

    async def event_ready(self) -> None:
        logger.info("Connected to Twitch chat as %s", self.nick)

    async def event_message(self, message: Message) -> None:  # type: ignore[override]
        if message.echo or message.author is None:
            return

        self._counter += 1
        if self._sample_rate > 1 and self._counter % self._sample_rate != 0:
            return

        payload = {
            "username": message.author.name,
            "display_name": message.author.display_name or message.author.name,
            "content": message.content,
            "tags": message.tags or {},
            "channel": self._channel,
            "timestamp": message.timestamp.timestamp() if message.timestamp else None,
        }
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("Message queue full, dropping chat message.")

    async def shutdown(self) -> None:
        logger.info("Shutting down Twitch chat client for #%s", self._channel)
        await self.close()
