"""All Gemini API interactions live here.

Each public function takes its API key explicitly — no hidden globals — so
the call site is responsible for handing credentials in. That keeps this
module testable and safe to import from anywhere.
"""

from __future__ import annotations

import json
from typing import Iterator

import google.generativeai as genai

from .models import Chapter, SentimentResult
from .prompts import (
    CHAPTERS_PROMPT,
    DETAIL_STYLES,
    HINT_LIST,
    HINT_OVERVIEW,
    HINT_SUMMARY,
    SENTIMENT_PROMPT,
    SUMMARY_PROMPT,
    SYSTEM_INSTRUCTION,
    TONE_STYLES,
)


# ── Question-type heuristics ─────────────────────────────────────────────────
# These short word lists pick up the most common cases where the model
# benefits from an explicit hint to "scan the whole transcript".
_OVERVIEW_WORDS = {
    "topic", "topics", "covered", "about", "discuss", "mention",
    "talk about", "go over", "goes over", "touch on",
}
_SUMMARY_WORDS = {"summar", "overview", "tldr", "tl;dr", "recap", "gist"}
_LIST_WORDS = {"list", "enumerate", "all the", "every", "complete list"}


def _hint_for_question(question: str) -> str:
    q = question.lower()
    if any(w in q for w in _OVERVIEW_WORDS):
        return HINT_OVERVIEW
    if any(w in q for w in _SUMMARY_WORDS):
        return HINT_SUMMARY
    if any(w in q for w in _LIST_WORDS):
        return HINT_LIST
    return ""


# ── Model factory ────────────────────────────────────────────────────────────
def _build_model(api_key: str, model_name: str):
    if not api_key or not api_key.strip():
        raise ValueError("API key is required.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
    )


# ── JSON-cleanup helper ──────────────────────────────────────────────────────
# Gemini sometimes wraps JSON in ```json fences, sometimes not. This handles both.
def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    # Strip first and last fence; tolerate "```json" prefix.
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


# ── One-shot calls ───────────────────────────────────────────────────────────
def generate_summary(api_key: str, transcript: str, model_name: str) -> str:
    """A 2-3 sentence overview of the video. Never raises — returns a fallback."""
    if not transcript.strip():
        return "No transcript available for summary."
    try:
        model = _build_model(api_key, model_name)
        # 15k chars is enough for a high-level summary; full read happens in chat.
        prompt = SUMMARY_PROMPT.format(transcript=transcript[:15_000])
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text or "Unable to generate summary."
    except Exception as exc:
        return f"Summary unavailable ({type(exc).__name__})."


def generate_chapters(
    api_key: str, timestamped_transcript: str, model_name: str
) -> list[Chapter]:
    """Detect chapters. Returns [] if none are clearly present or the call fails."""
    if not timestamped_transcript.strip():
        return []
    try:
        model = _build_model(api_key, model_name)
        prompt = CHAPTERS_PROMPT.format(transcript=timestamped_transcript[:30_000])
        response = model.generate_content(prompt)
        raw = _strip_code_fences(response.text or "")
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [
            Chapter(time=str(d["time"]), title=str(d["title"]))
            for d in data
            if isinstance(d, dict) and "time" in d and "title" in d
        ]
    except (json.JSONDecodeError, KeyError, Exception):
        return []


def analyze_sentiment(
    api_key: str, comments: list[str], model_name: str
) -> SentimentResult:
    """Bulk sentiment across up to 150 comments. Returns a neutral fallback on error."""
    if not comments:
        return SentimentResult(label="N/A", score=-1)
    try:
        model = _build_model(api_key, model_name)
        sample = comments[:150]
        prompt = SENTIMENT_PROMPT.format(
            count=len(sample),
            comments="\n---\n".join(sample),
        )
        response = model.generate_content(prompt)
        raw = _strip_code_fences(response.text or "")
        if not raw:
            return SentimentResult(label="Mixed", score=50)
        data = json.loads(raw)
        label = str(data.get("label", "Mixed"))
        score = max(0, min(100, int(data.get("score", 50))))
        return SentimentResult(label=label, score=score)
    except Exception:
        return SentimentResult(label="Mixed", score=50)


# ── Conversational chat with streaming ───────────────────────────────────────
def _build_chat_prompt(
    *,
    transcript_block: str,
    summary: str,
    history: list[dict],
    question: str,
    detail: str,
    tone: str,
    has_timestamps: bool,
) -> str:
    """Compose the full chat prompt. Pure string assembly, easy to test."""
    style = (
        f"{DETAIL_STYLES.get(detail, DETAIL_STYLES['standard'])}\n"
        f"{TONE_STYLES.get(tone, TONE_STYLES['neutral'])}"
    )

    history_text = ""
    if history:
        for turn in history[-8:]:  # last 8 turns is plenty of context
            role = "User" if turn["role"] == "user" else "Assistant"
            history_text += f"{role}: {turn['content']}\n\n"

    ts_note = (
        "Timestamps are in [MM:SS] format. Reference them in your answer."
        if has_timestamps
        else "No timestamps available for this transcript."
    )

    hint = _hint_for_question(question)
    history_section = (
        f"PREVIOUS CONVERSATION:\n{history_text}" if history_text else ""
    )

    return (
        f"{style}\n\n"
        f"{hint}\n\n"
        f"{ts_note}\n\n"
        f"---\n{transcript_block}\n---\n\n"
        f"VIDEO OVERVIEW: {summary}\n\n"
        f"{history_section}"
        f"User: {question}\n\nAnswer:"
    )


def chat_stream(
    *,
    api_key: str,
    model_name: str,
    transcript_block: str,
    summary: str,
    history: list[dict],
    question: str,
    detail: str = "standard",
    tone: str = "neutral",
    has_timestamps: bool = True,
) -> Iterator[str]:
    """Yield response chunks as the model produces them.

    Streaming makes the UI feel alive and lets the user start reading
    before the full answer lands.
    """
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    model = _build_model(api_key, model_name)
    prompt = _build_chat_prompt(
        transcript_block=transcript_block,
        summary=summary,
        history=history,
        question=question,
        detail=detail,
        tone=tone,
        has_timestamps=has_timestamps,
    )

    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        text = getattr(chunk, "text", "") or ""
        if text:
            yield text
