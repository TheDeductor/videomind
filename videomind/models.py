"""Data models for VideoMind.

Everything that gets passed between modules lives here. Keeping these in one
place makes it obvious what shape the state has at any given moment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DetailLevel(str, Enum):
    """How verbose the AI's answers should be."""

    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"


class Tone(str, Enum):
    """Stylistic register for AI answers."""

    NEUTRAL = "neutral"
    CONVERSATIONAL = "conversational"
    ACADEMIC = "academic"


class Theme(str, Enum):
    DARK = "dark"
    LIGHT = "light"


@dataclass
class TranscriptSegment:
    """One captioned line from YouTube, with its start time."""

    start: float
    text: str
    time_str: str  # human-readable, e.g. "2:35" or "1:02:35"


@dataclass
class Chapter:
    """An auto-detected chapter in the video."""

    time: str  # "2:30"
    title: str


@dataclass
class SentimentResult:
    label: str  # e.g. "Positive", "Mixed"
    score: int  # 0..100, or -1 if not analyzed


@dataclass
class VideoContext:
    """Everything we know about a loaded video.

    Held in `st.session_state.ctx` for the lifetime of a session.
    """

    video_id: str
    plain_transcript: str
    timestamped_transcript: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    has_timestamps: bool = True

    # AI-derived metadata
    summary: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    sentiment: SentimentResult = field(
        default_factory=lambda: SentimentResult(label="", score=-1)
    )
    sentiment_done: bool = False

    # RAG state (populated only for long transcripts)
    rag_collection: Any = None  # chromadb.Collection — typed loosely to avoid import
    use_rag: bool = False

    @property
    def is_manual(self) -> bool:
        """True when the user pasted the transcript by hand."""
        return self.video_id == "manual"

    @property
    def word_count(self) -> int:
        return len(self.plain_transcript.split())

    @property
    def thumbnail_url(self) -> str | None:
        """YouTube provides predictable thumbnail URLs by video ID."""
        if self.is_manual:
            return None
        return f"https://img.youtube.com/vi/{self.video_id}/mqdefault.jpg"
