from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Common Twitch vernacular for lightweight sentiment adjustments
POSITIVE_BOOST = {"gg", "pog", "poggers", "w", "based", "clutch", "lets", "nice"}
NEGATIVE_BOOST = {"l", "cringe", "fail", "cope", "mald", "trash", "worst", "lost"}

KNOWN_TEXTUAL_EMOTES = {
    "KEKW",
    "LUL",
    "OMEGALUL",
    "PogChamp",
    "POGGERS",
    "Kappa",
    "FeelsBadMan",
    "FeelsGoodMan",
    "BibleThump",
    "PogU",
    "monkaS",
    "monkaW",
    "PepeHands",
    "PepeLaugh",
    "Pepega",
    "PeepoClap",
    "Clap",
    "HeyGuys",
    "4Head",
}

COMMAND_REGEX = re.compile(r"^![a-zA-Z0-9_]+")


@dataclass
class AnalysisResult:
    sentiment_label: str
    sentiment_score: float
    emotes: List[Tuple[str, str]]


class MessageAnalyzer:
    """Runs sentiment analysis and emote extraction for chat messages."""

    def __init__(self) -> None:
        self._sentiment = SentimentIntensityAnalyzer()

    def analyze(self, content: str, tags: Dict[str, str] | None = None) -> AnalysisResult:
        tags = tags or {}
        sentiment_label, sentiment_score = self._score_sentiment(content)
        emotes = self._extract_emotes(content, tags)
        return AnalysisResult(sentiment_label=sentiment_label, sentiment_score=sentiment_score, emotes=emotes)

    def _score_sentiment(self, content: str) -> Tuple[str, float]:
        text = content.strip()
        if not text or COMMAND_REGEX.match(text):
            return "neutral", 0.0

        scores = self._sentiment.polarity_scores(text)
        compound = scores["compound"]
        lowered = text.lower()

        tokens = {token.strip("!,?.") for token in re.split(r"\s+", lowered) if token}
        if POSITIVE_BOOST & tokens:
            compound += 0.1
        if NEGATIVE_BOOST & tokens:
            compound -= 0.1

        compound = max(min(compound, 1.0), -1.0)
        if compound >= 0.05:
            return "positive", compound
        if compound <= -0.05:
            return "negative", compound
        return "neutral", compound

    def _extract_emotes(self, content: str, tags: Dict[str, str]) -> List[Tuple[str, str]]:
        emote_tag = tags.get("emotes")
        emotes: List[Tuple[str, str]] = []

        if emote_tag:
            for entry in emote_tag.split("/"):
                if not entry:
                    continue
                parts = entry.split(":")
                if len(parts) != 2:
                    continue
                emote_id, positions = parts
                for span in positions.split(","):
                    if not span:
                        continue
                    start_end = span.split("-")
                    if len(start_end) != 2:
                        continue
                    try:
                        start, end = int(start_end[0]), int(start_end[1])
                    except ValueError:
                        continue
                    name = content[start : end + 1]
                    emotes.append((emote_id, name))

        if not emotes:
            for token in re.findall(r"[A-Za-z0-9_]+", content):
                if token in KNOWN_TEXTUAL_EMOTES or token.upper() in KNOWN_TEXTUAL_EMOTES:
                    canon = token if token in KNOWN_TEXTUAL_EMOTES else token.upper()
                    emotes.append((canon, canon))

        return emotes

