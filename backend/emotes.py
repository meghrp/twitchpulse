from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmoteService:
    """Fetches and caches Twitch emote metadata for richer UI rendering."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)
        self._app_token: Optional[str] = settings.twitch_app_token
        self._token_expiry: float = time.time()
        self._cache: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()

    async def warm_cache(self) -> None:
        if not settings.twitch_client_id or not settings.twitch_client_secret:
            logger.info("Skipping Twitch emote warm cache; credentials not configured.")
            return
        try:
            await self._ensure_app_token()
            await self._fetch_global_emotes()
        except httpx.HTTPError as exc:
            logger.warning("Unable to warm Twitch emote cache: %s", exc)

    async def _ensure_app_token(self) -> None:
        if self._app_token and self._token_expiry - time.time() > 60:
            return

        if settings.twitch_client_id and settings.twitch_client_secret:
            payload = {
                "client_id": settings.twitch_client_id,
                "client_secret": settings.twitch_client_secret,
                "grant_type": "client_credentials",
            }
            response = await self._client.post("https://id.twitch.tv/oauth2/token", data=payload)
            response.raise_for_status()
            data = response.json()
            self._app_token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600)
            logger.info("Fetched new Twitch app token.")

    async def _fetch_global_emotes(self) -> None:
        if not self._app_token:
            return
        headers = {
            "Client-ID": settings.twitch_client_id,
            "Authorization": f"Bearer {self._app_token}",
        }
        response = await self._client.get("https://api.twitch.tv/helix/chat/emotes/global", headers=headers)
        response.raise_for_status()
        payload = response.json()
        for entry in payload.get("data", []):
            self._cache[entry["id"]] = {
                "id": entry["id"],
                "name": entry["name"],
                "imageUrl": entry.get("images", {}).get("url_2x")
                or entry.get("images", {}).get("url_1x")
                or _cdn_url(entry["id"]),
            }
        logger.info("Cached %s global Twitch emotes.", len(self._cache))

    async def get_emote_metadata(self, emote_id: str, fallback_name: Optional[str] = None) -> Dict[str, str]:
        if not emote_id:
            return {"id": "", "name": fallback_name or "", "imageUrl": ""}

        cached = self._cache.get(emote_id)
        if cached:
            return cached

        # If not cached, attempt on-demand fetch when credentials exist.
        if settings.twitch_client_id and settings.twitch_client_secret:
            async with self._lock:
                cached = self._cache.get(emote_id)
                if cached:
                    return cached
                await self._ensure_app_token()
                if self._app_token:
                    headers = {
                        "Client-ID": settings.twitch_client_id,
                        "Authorization": f"Bearer {self._app_token}",
                    }
                    response = await self._client.get(
                        "https://api.twitch.tv/helix/chat/emotes",
                        params={"id": emote_id},
                        headers=headers,
                    )
                    if response.status_code == 200:
                        data = response.json().get("data", [])
                        if data:
                            entry = data[0]
                            meta = {
                                "id": entry["id"],
                                "name": entry["name"],
                                "imageUrl": entry.get("images", {}).get("url_2x")
                                or entry.get("images", {}).get("url_1x")
                                or _cdn_url(entry["id"]),
                            }
                            self._cache[emote_id] = meta
                            return meta

        return {
            "id": emote_id,
            "name": fallback_name or emote_id,
            "imageUrl": _cdn_url(emote_id),
        }

    async def get_known_emotes(self, limit: int = 200) -> List[Dict[str, str]]:
        if not self._cache:
            return []
        return list(self._cache.values())[:limit]

    async def close(self) -> None:
        await self._client.aclose()


def _cdn_url(emote_id: str, theme: str = "dark", scale: str = "2.0") -> str:
    return f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/{theme}/{scale}"

