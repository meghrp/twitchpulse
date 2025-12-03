from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .analyzer import MessageAnalyzer
from .config import get_settings
from .emotes import EmoteService
from .models import StartSessionRequest, StartSessionResponse, StopSessionRequest
from .redis_manager import RedisManager
from .twitch_client import TwitchChatClient
from .seventv import SevenTVService

logger = logging.getLogger("twitchpulse")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")

settings = get_settings()
redis_manager = RedisManager()
analyzer = MessageAnalyzer()
emote_service = EmoteService()
seventv_service = SevenTVService()

app = FastAPI(title="TwitchPulse Chat Analyzer", default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class SessionState:
    session_id: str
    channel: str
    duration: int
    queue: asyncio.Queue
    bot: TwitchChatClient
    bot_task: asyncio.Task
    processor_task: asyncio.Task
    timer_task: asyncio.Task
    started_at: datetime


active_sessions: Dict[str, SessionState] = {}


@app.get("/health")
async def health() -> Dict[str, str]:
    await redis_manager.ping()
    return {"status": "ok"}


@app.on_event("startup")
async def _startup() -> None:
    await asyncio.gather(emote_service.warm_cache(), seventv_service.warm_globals())


@app.on_event("shutdown")
async def _shutdown() -> None:
    await asyncio.gather(emote_service.close(), seventv_service.close())


@app.get("/api/config")
async def config() -> Dict[str, int]:
    return {
        "defaultDuration": settings.default_duration_seconds,
        "maxDuration": settings.max_duration_seconds,
        "updateIntervalMs": settings.update_interval_ms,
        "messageSampleRate": settings.message_sample_rate,
    }


@app.get("/api/emotes/global")
async def global_emotes() -> Dict[str, List[Dict[str, str]]]:
    return {"items": await emote_service.get_known_emotes()}


@app.post("/api/start", response_model=StartSessionResponse)
async def start_session(payload: StartSessionRequest) -> StartSessionResponse:
    session_id = uuid.uuid4().hex
    duration = payload.duration_seconds

    await redis_manager.initialize_session(session_id, payload.channel, duration)
    asyncio.create_task(seventv_service.load_session(session_id, payload.channel))

    queue: asyncio.Queue = asyncio.Queue(maxsize=5_000)
    bot = TwitchChatClient(channel=payload.channel, message_queue=queue, sample_rate=payload.sample_rate)
    processor_task = asyncio.create_task(_message_worker(session_id, queue))
    timer_task = asyncio.create_task(_auto_stop(session_id, duration))
    bot_task = asyncio.create_task(_run_bot(session_id, bot))

    started_at = datetime.now(timezone.utc)

    active_sessions[session_id] = SessionState(
        session_id=session_id,
        channel=payload.channel,
        duration=duration,
        queue=queue,
        bot=bot,
        bot_task=bot_task,
        processor_task=processor_task,
        timer_task=timer_task,
        started_at=started_at,
    )

    expires_at = started_at + timedelta(seconds=duration)
    return StartSessionResponse(
        session_id=session_id,
        status="active",
        channel=payload.channel,
        duration_seconds=duration,
        started_at=started_at,
        expires_at=expires_at,
    )


@app.post("/api/stop")
async def stop_session(payload: StopSessionRequest) -> Dict[str, str]:
    if payload.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    await _stop_session(payload.session_id, from_timer=False)
    return {"status": "stopped", "sessionId": payload.session_id}


@app.get("/api/stats/{session_id}")
async def get_stats(session_id: str) -> Dict:
    stats = await redis_manager.get_stats(session_id)
    if not stats or not stats.get("session"):
        raise HTTPException(status_code=404, detail="Session stats unavailable")
    return stats


@app.websocket("/ws/{session_id}")
async def stats_socket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    interval = max(settings.update_interval_ms / 1000, 0.25)
    try:
        while True:
            stats = await redis_manager.get_stats(session_id)
            await websocket.send_json(stats)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as exc:  # pragma: no cover - logging only
        logger.error("WebSocket error for session %s: %s", session_id, exc)
    finally:
        with suppress(Exception):
            await websocket.close()


async def _message_worker(session_id: str, queue: asyncio.Queue) -> None:
    logger.info("Starting message worker for session %s", session_id)
    try:
        while True:
            message = await queue.get()
            terminate = message is None
            try:
                if not terminate:
                    content: str = message.get("content", "")
                    tags = message.get("tags") or {}

                    await redis_manager.increment_message_count(session_id)
                    await redis_manager.increment_chatter(session_id, message.get("username", "anonymous"))

                    analysis = analyzer.analyze(content, tags)
                batched_emotes = list(analysis.emotes)
                custom_emotes = seventv_service.match_message(session_id, content)
                if custom_emotes:
                    for emote in custom_emotes:
                        batched_emotes.append((emote.key, emote.name))
                if batched_emotes:
                    await redis_manager.increment_emotes(session_id, batched_emotes)
                if analysis.emotes:
                    await _cache_emote_images(session_id, analysis.emotes)
                if custom_emotes:
                    for emote in custom_emotes:
                        await redis_manager.set_emote_image(session_id, emote.key, emote.image_url)
                    await redis_manager.update_sentiment(session_id, analysis.sentiment_label, analysis.sentiment_score)

                    timestamp = int(message.get("timestamp") or datetime.now(timezone.utc).timestamp())
                    await redis_manager.append_timeline(session_id, timestamp)
            finally:
                queue.task_done()
            if terminate:
                break
    except asyncio.CancelledError:  # graceful shutdown
        logger.info("Message worker for %s cancelled", session_id)
    except Exception as exc:
        logger.exception("Worker error for session %s: %s", session_id, exc)
    finally:
        logger.info("Message worker for %s finished", session_id)


async def _auto_stop(session_id: str, duration: int) -> None:
    await asyncio.sleep(duration)
    await _stop_session(session_id, from_timer=True)


async def _stop_session(session_id: str, *, from_timer: bool) -> None:
    state = active_sessions.pop(session_id, None)
    if not state:
        return

    logger.info("Stopping session %s", session_id)
    sentinel_sent = False
    with suppress(asyncio.QueueFull):
        state.queue.put_nowait(None)
        sentinel_sent = True
    if not sentinel_sent:
        state.processor_task.cancel()
    with suppress(asyncio.CancelledError):
        await state.processor_task

    if not from_timer:
        with suppress(asyncio.CancelledError):
            state.timer_task.cancel()

    await state.bot.shutdown()
    with suppress(asyncio.CancelledError):
        await state.bot_task
    status = "complete" if from_timer else "stopped"
    await redis_manager.close_session(session_id, status=status)
    await redis_manager.append_timeline(session_id, int(datetime.now(timezone.utc).timestamp()))
    await seventv_service.drop_session(session_id)


async def _run_bot(session_id: str, bot: TwitchChatClient) -> None:
    try:
        await bot.start()
    except asyncio.CancelledError:
        logger.info("Bot task for %s cancelled", session_id)
    except Exception as exc:
        logger.error("Bot connection error for %s: %s", session_id, exc)


async def _cache_emote_images(session_id: str, emotes: List[Tuple[str, str]]) -> None:
    unique = {emote_id: name for emote_id, name in emotes}
    for emote_id, emote_name in unique.items():
        if not emote_id.isdigit():
            await redis_manager.set_emote_image(session_id, emote_id, "")
            continue
        meta = await emote_service.get_emote_metadata(emote_id, emote_name)
        if meta.get("imageUrl"):
            await redis_manager.set_emote_image(session_id, emote_id, meta["imageUrl"])

