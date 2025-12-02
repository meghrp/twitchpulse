"""Synthetic load generator for validating Redis + analyzer performance."""

from __future__ import annotations

import argparse
import asyncio
import random
import time
import uuid

from .analyzer import MessageAnalyzer
from .redis_manager import RedisManager

EMOTES = ["Kappa", "PogChamp", "KEKW", "LUL", "BibleThump", "FeelsGoodMan"]
MESSAGES = [
    "That play was insane PogChamp",
    "KEKW what was that",
    "gg wp team, lets gooo",
    "this strat is so cringe",
    "I love this community BibleThump",
    "POGGERS massive W",
    "why did he do that LUL",
]


async def run_simulation(count: int, channel: str, duration: int) -> str:
    session_id = uuid.uuid4().hex
    redis_manager = RedisManager()
    analyzer = MessageAnalyzer()

    await redis_manager.initialize_session(session_id, channel, duration)
    start = time.time()

    for index in range(count):
        username = f"user_{index % 150}"
        message = random.choice(MESSAGES)
        if random.random() > 0.6:
            message += f" {random.choice(EMOTES)}"
        analysis = analyzer.analyze(message, {})
        await redis_manager.increment_message_count(session_id)
        await redis_manager.increment_chatter(session_id, username)
        if analysis.emotes:
            await redis_manager.increment_emotes(session_id, analysis.emotes)
        await redis_manager.update_sentiment(session_id, analysis.sentiment_label, analysis.sentiment_score)
        await redis_manager.append_timeline(session_id, int(time.time()))

    elapsed = time.time() - start
    print(f"Inserted {count} synthetic messages in {elapsed:.2f}s (session {session_id}).")
    return session_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Twitch chat load for testing.")
    parser.add_argument("--count", type=int, default=5000, help="Total fake messages to insert.")
    parser.add_argument("--channel", type=str, default="testchannel", help="Channel label.")
    parser.add_argument("--duration", type=int, default=120, help="Virtual duration for the session.")
    args = parser.parse_args()

    session_id = asyncio.run(run_simulation(args.count, args.channel, args.duration))
    print(f"Session ready. Connect UI with session ID: {session_id}")


if __name__ == "__main__":
    main()

