"""YouTube data access: video ID parsing, transcript fetching, comment fetching.

These are the only functions in the codebase that touch YouTube's APIs.
Everything is pure (no Streamlit, no global state) so it can be cached at the
call site.
"""

from __future__ import annotations

import re
from typing import Iterable

from youtube_comment_downloader import YoutubeCommentDownloader
from youtube_transcript_api import YouTubeTranscriptApi

from .models import TranscriptSegment


# YouTube video IDs are exactly 11 chars from [A-Za-z0-9_-].
_ID_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/embed/([A-Za-z0-9_-]{11})"),
)


def extract_video_id(url: str) -> str:
    """Return the 11-character video ID, or raise ValueError on garbage input."""
    url = (url or "").strip()
    if not url:
        raise ValueError("Please paste a YouTube URL.")
    for pat in _ID_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1)
    # Bare ID? Accept it if it looks right — saves a click for power users.
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    raise ValueError("Couldn't parse a YouTube video ID from that URL.")


def _format_timestamp(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS — matches YouTube's own convention."""
    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def _parse_snippets(snippets: Iterable) -> tuple[str, str, list[TranscriptSegment]]:
    """Convert raw transcript snippets into plain text, [ts] text, and segments."""
    segments: list[TranscriptSegment] = []
    plain_lines: list[str] = []
    ts_lines: list[str] = []

    for s in snippets:
        text = s.text.strip()
        if not text:
            continue
        ts = _format_timestamp(s.start)
        segments.append(TranscriptSegment(start=s.start, text=text, time_str=ts))
        plain_lines.append(text)
        ts_lines.append(f"[{ts}] {text}")

    return "\n".join(plain_lines), "\n".join(ts_lines), segments


def fetch_transcript(
    video_id: str,
    preferred_languages: list[str] | None = None,
) -> tuple[str, str, list[TranscriptSegment]]:
    """Fetch transcript, falling back across languages until something works.

    Returns (plain_text, timestamped_text, segments). All empty if nothing
    is available — the caller decides what to do.
    """
    languages = preferred_languages or ["en", "en-US", "en-GB"]
    api = YouTubeTranscriptApi()

    # Attempt 1: preferred languages.
    try:
        return _parse_snippets(api.fetch(video_id, languages=languages))
    except Exception:
        pass

    # Attempt 2: whatever's available, no language pinning.
    try:
        return _parse_snippets(api.fetch(video_id))
    except Exception:
        pass

    # Attempt 3: walk the list of all transcripts and grab the first that fetches.
    try:
        for transcript in api.list(video_id):
            try:
                return _parse_snippets(transcript.fetch())
            except Exception:
                continue
    except Exception:
        pass

    return "", "", []


def fetch_comments(video_url: str, max_comments: int = 200) -> list[str]:
    """Pull top-level comment text from a video. Best-effort: returns [] on failure."""
    try:
        downloader = YoutubeCommentDownloader()
        stream = downloader.get_comments_from_url(video_url, sort_by=0)
    except Exception:
        return []

    out: list[str] = []
    for item in stream:
        text = (item.get("text") or "").strip()
        if text:
            out.append(text)
        if len(out) >= max_comments:
            break
    return out
