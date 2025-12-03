from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SevenTVLookup:
    by_name: Dict[str, Dict[str, str]]
    by_id: Dict[str, Dict[str, str]]

    @classmethod
    def empty(cls) -> "SevenTVLookup":
        return cls({}, {})


class EmoteService:
    """Fetches and caches Twitch emote metadata for richer UI rendering."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)
        self._app_token: Optional[str] = settings.twitch_app_token
        self._token_expiry: float = time.time()
        self._cache: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()
        self._twitch_user_cache: Dict[str, str] = {}
        self._seven_tv_global: Dict[str, Dict[str, str]] = {}
        self._seven_tv_channel: Dict[str, Dict[str, str]] = {}
        self._seven_tv_lock = asyncio.Lock()

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
            response = await self._client.post(
                "https://id.twitch.tv/oauth2/token", data=payload
            )
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
        response = await self._client.get(
            "https://api.twitch.tv/helix/chat/emotes/global", headers=headers
        )
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

    async def get_twitch_user_id(self, channel_login: str) -> Optional[str]:
        login = channel_login.lower()
        if login in self._twitch_user_cache:
            return self._twitch_user_cache[login]
        if not settings.twitch_client_id or not settings.twitch_client_secret:
            return None
        await self._ensure_app_token()
        if not self._app_token:
            return None
        headers = {
            "Client-ID": settings.twitch_client_id,
            "Authorization": f"Bearer {self._app_token}",
        }
        response = await self._client.get(
            "https://api.twitch.tv/helix/users",
            params={"login": login},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return None
        user_id = data[0]["id"]
        self._twitch_user_cache[login] = user_id
        return user_id

    async def get_emote_metadata(
        self, emote_id: str, fallback_name: Optional[str] = None
    ) -> Dict[str, str]:
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

    async def get_seven_tv_emotes(self, twitch_user_id: Optional[str]) -> SevenTVLookup:
        await self._ensure_seven_tv_global()
        by_name: Dict[str, Dict[str, str]] = dict(self._seven_tv_global)
        if twitch_user_id:
            channel_map = await self._get_seven_tv_channel_emotes(twitch_user_id)
            by_name.update(channel_map)
        by_id = {meta["id"]: meta for meta in by_name.values()}
        return SevenTVLookup(by_name=by_name, by_id=by_id)

    async def close(self) -> None:
        await self._client.aclose()

    async def _ensure_seven_tv_global(self) -> None:
        if self._seven_tv_global:
            return
        async with self._seven_tv_lock:
            if self._seven_tv_global:
                return
            try:
                response = await self._client.get("https://7tv.io/v3/emote-sets/global")
                response.raise_for_status()
                self._seven_tv_global = self._normalize_seven_tv_emotes(response.json())
                logger.info("Cached %s 7TV global emotes.", len(self._seven_tv_global))
            except httpx.HTTPError as exc:
                logger.warning("Unable to load 7TV global emotes: %s", exc)
                self._seven_tv_global = {}

    async def _get_seven_tv_channel_emotes(
        self, twitch_user_id: str
    ) -> Dict[str, Dict[str, str]]:
        if twitch_user_id in self._seven_tv_channel:
            return self._seven_tv_channel[twitch_user_id]
        async with self._seven_tv_lock:
            if twitch_user_id in self._seven_tv_channel:
                return self._seven_tv_channel[twitch_user_id]
            try:
                response = await self._client.get(
                    f"https://7tv.io/v3/users/twitch/{twitch_user_id}"
                )
                response.raise_for_status()
                payload = response.json()
                emote_set = (payload.get("emote_set") or {}).get("emotes", [])
                normalized = self._normalize_seven_tv_emotes({"emotes": emote_set})
                self._seven_tv_channel[twitch_user_id] = normalized
                return normalized
            except httpx.HTTPError as exc:
                logger.warning(
                    "Unable to load 7TV emotes for %s: %s", twitch_user_id, exc
                )
                self._seven_tv_channel[twitch_user_id] = {}
                return {}

    def _normalize_seven_tv_emotes(
        self, payload: Dict[str, List[Dict[str, str]]]
    ) -> Dict[str, Dict[str, str]]:
        emotes = payload.get("emotes") or []
        result: Dict[str, Dict[str, str]] = {}
        for entry in emotes:
            emote_id = entry.get("id")
            name = entry.get("name")
            if not emote_id or not name:
                continue
            image_url = _seven_tv_cdn_url(entry)
            result[name.lower()] = {
                "provider": "7tv",
                "id": emote_id,
                "name": name,
                "imageUrl": image_url,
            }
        return result


def _cdn_url(emote_id: str, theme: str = "dark", scale: str = "2.0") -> str:
    return (
        f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/{theme}/{scale}"
    )


def _seven_tv_cdn_url(entry: Dict[str, str], size: str = "2x") -> str:
    host = entry.get("host") or {}
    base_url = host.get("url")
    files = host.get("files") or []
    target_format = "webp"
    for file in files:
        if file.get("name") == size:
            target_format = file.get("format", "webp").lower()
            break
    if base_url:
        if base_url.startswith("//"):
            base_url = f"https:{base_url}"
        elif not base_url.startswith("http"):
            base_url = f"https://{base_url.lstrip('/')}"
        return f"{base_url}/{size}.{target_format}"
    return f"https://cdn.7tv.app/emote/{entry.get('id')}/{size}.webp"
