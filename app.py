"""VideoMind — chat with any YouTube video using AI.

This module is the Streamlit entry point. It only does three things:
  1. Wire up session state and the sidebar.
  2. Render the "setup" view (URL input) or the "chat" view, depending on state.
  3. Dispatch user actions to functions in `ai`, `youtube`, and `rag`.

All AI calls live in `ai.py`. All YouTube I/O lives in `youtube.py`. Keeping
this file thin makes the user flow legible at a glance.
"""

from __future__ import annotations

import html
import os
import time
from typing import Iterator

import streamlit as st

try:
    import markdown as md_lib

    def render_markdown(text: str) -> str:
        return md_lib.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
except ImportError:
    def render_markdown(text: str) -> str:
        return html.escape(text).replace("\n", "<br>")

from videomind import ai, rag, youtube
from videomind.config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    DEFAULT_SUGGESTIONS,
    FULL_TRANSCRIPT_LIMIT,
    SENTIMENT_COMMENT_LIMIT,
    TRANSCRIPT_CACHE_TTL,
)
from videomind.models import Theme, VideoContext
from videomind.theme import build_css


# ─── PAGE & THEME ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VideoMind — AI Video Expert",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── SESSION-STATE DEFAULTS ──────────────────────────────────────────────────
# Everything the app reads from `st.session_state` is declared here, so future
# readers can find it without grep.
_DEFAULTS = {
    "ctx": None,                                 # VideoContext | None
    "ready": False,                              # has a video been loaded?
    "chat_history": [],                          # list of {role, content}
    "pending_q": "",                             # set by chip clicks
    "need_manual": False,                        # show manual-transcript form?
    "gemini_key": os.getenv("GEMINI_API_KEY", ""),  # API key from .env if set
    "theme": Theme.DARK.value,
    "model_name": DEFAULT_MODEL,
    "detail_level": "standard",
    "tone_level": "neutral",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── INJECT CSS ──────────────────────────────────────────────────────────────
_current_theme = Theme(st.session_state.theme)
st.markdown(build_css(_current_theme), unsafe_allow_html=True)


# ─── CACHED I/O ──────────────────────────────────────────────────────────────
# Streamlit caches the *return value* keyed on the function args. Transcripts
# never change for a given video ID, so this is safe and a big win on reruns.

@st.cache_data(show_spinner=False, ttl=TRANSCRIPT_CACHE_TTL)
def cached_fetch_transcript(video_id: str) -> tuple[str, str, list]:
    """Cached wrapper around `youtube.fetch_transcript`."""
    plain, ts, segs = youtube.fetch_transcript(video_id)
    # Convert dataclass segments to a serialisable form for the cache.
    return plain, ts, [(s.start, s.text, s.time_str) for s in segs]


def _segments_from_cached(raw: list) -> list:
    """Reconstruct TranscriptSegment dataclasses from the cached tuple form."""
    from videomind.models import TranscriptSegment
    return [TranscriptSegment(start=s, text=t, time_str=ts) for s, t, ts in raw]


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand"><h1>VideoMind</h1><p>AI Video Expert</p></div>',
            unsafe_allow_html=True,
        )

        # API key (also accepts .env via GEMINI_API_KEY)
        st.markdown('<p class="sb-label">API Configuration</p>', unsafe_allow_html=True)
        st.session_state.gemini_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_key,
            type="password",
            placeholder="AIza...",
            help=(
                "Get a free key from https://aistudio.google.com/app/apikey. "
                "Tip: set GEMINI_API_KEY in a .env file to skip this step."
            ),
        )

        st.selectbox(
            "Model",
            AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(DEFAULT_MODEL),
            key="model_name",
            help="Flash = faster & cheaper. Pro = more capable.",
        )

        # Response shape (only relevant once a video is loaded)
        if st.session_state.ready:
            st.markdown('<p class="sb-label">Response Settings</p>', unsafe_allow_html=True)
            st.selectbox(
                "Detail level",
                ["concise", "standard", "detailed"],
                index=1,
                key="detail_level",
            )
            st.selectbox(
                "Tone",
                ["neutral", "conversational", "academic"],
                index=0,
                key="tone_level",
            )

        # Theme toggle
        st.markdown('<p class="sb-label">Appearance</p>', unsafe_allow_html=True)
        is_dark = st.toggle("Dark mode", value=(_current_theme == Theme.DARK))
        new_theme = Theme.DARK if is_dark else Theme.LIGHT
        if new_theme.value != st.session_state.theme:
            st.session_state.theme = new_theme.value
            st.rerun()

        # Session controls
        if st.session_state.ready:
            st.markdown("---")
            st.markdown('<p class="sb-label">Session</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="sb-act">', unsafe_allow_html=True)
                if st.button("Clear chat", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="sb-act">', unsafe_allow_html=True)
                if st.button("Reset all", key="reset_all"):
                    for k, v in _DEFAULTS.items():
                        # Preserve API key & theme on reset — those are user prefs
                        if k in ("gemini_key", "theme"):
                            continue
                        st.session_state[k] = v
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            ctx: VideoContext = st.session_state.ctx
            wc = ctx.word_count if ctx else 0
            turns = len(st.session_state.chat_history) // 2
            mode = "RAG" if (ctx and ctx.use_rag) else "Full"
            st.markdown(
                f'<p style="font-size:.7rem;color:var(--t3);margin-top:.6rem">'
                f"{wc:,} words · {turns} Q&A turns · {mode} context"
                f"</p>",
                unsafe_allow_html=True,
            )


render_sidebar()


# ─── ERROR PRETTIFIER ────────────────────────────────────────────────────────
def humanize_error(exc: Exception) -> str:
    """Turn raw Gemini errors into something a user can act on."""
    msg = str(exc)
    low = msg.lower()
    if "api_key_invalid" in low or " 401" in low:
        return "Invalid API key. Please check it in the sidebar."
    if "resource_exhausted" in low or " 429" in low:
        return "Rate limit hit. Wait a few seconds and try again."
    if "quota" in low:
        return "API quota exceeded. Check your Google AI Studio quota."
    if "permission_denied" in low or " 403" in low:
        return "Permission denied. The API key may be restricted."
    if "timeout" in low:
        return "The request timed out. The video may be too long."
    return f"Something went wrong: {msg[:200]}"


# ─── STREAMING HELPER ────────────────────────────────────────────────────────
def stream_into_placeholder(
    placeholder, chunk_iter: Iterator[str]
) -> str:
    """Stream chunks into a Streamlit placeholder, returning the final text."""
    buffer = []
    for chunk in chunk_iter:
        buffer.append(chunk)
        joined = "".join(buffer)
        placeholder.markdown(
            f'<div class="aa">{render_markdown(joined)}<span class="cursor">▍</span></div>',
            unsafe_allow_html=True,
        )
    final = "".join(buffer).strip() or "I couldn't generate a response. Please try rephrasing."
    placeholder.markdown(
        f'<div class="aa">{render_markdown(final)}</div>',
        unsafe_allow_html=True,
    )
    return final


# ─── PAGE HEADER ─────────────────────────────────────────────────────────────
st.markdown(
    '<div class="pg-h"><h1>VideoMind</h1>'
    "<p>Chat with any YouTube video using AI.</p></div>",
    unsafe_allow_html=True,
)


# ═════════════════════════════════════════════════════════════════════════════
# SETUP PHASE — no video loaded yet
# ═════════════════════════════════════════════════════════════════════════════
def render_setup_phase() -> None:
    url_input = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
        key="url_input",
    )
    col_load, _ = st.columns([1, 5])
    with col_load:
        load_clicked = st.button("Analyze video", type="primary", use_container_width=True)

    if load_clicked:
        _handle_analyze(url_input)

    if st.session_state.need_manual:
        _render_manual_fallback()


def _handle_analyze(url_input: str) -> None:
    """Validate input, fetch the transcript, and build a VideoContext."""
    if not url_input.strip():
        st.error("Please paste a YouTube URL first.")
        return
    if not st.session_state.gemini_key:
        st.error("Please enter your Gemini API key in the sidebar.")
        return

    try:
        video_id = youtube.extract_video_id(url_input)
    except ValueError as e:
        st.error(str(e))
        return

    api_key = st.session_state.gemini_key
    model = st.session_state.model_name

    with st.spinner("Fetching transcript..."):
        plain, ts_text, raw_segs = cached_fetch_transcript(video_id)
        segments = _segments_from_cached(raw_segs)

    if not plain.strip():
        st.session_state.need_manual = True
        st.warning(
            "Auto-transcript unavailable (captions may be disabled or in an "
            "unsupported language). You can paste the transcript manually below."
        )
        return

    with st.spinner("Analyzing video content..."):
        summary = ai.generate_summary(api_key, plain, model)
        chapters = ai.generate_chapters(api_key, ts_text, model)

    use_rag = len(ts_text) > FULL_TRANSCRIPT_LIMIT
    rag_collection = None
    if use_rag:
        with st.spinner("Indexing long transcript for retrieval..."):
            rag_collection = rag.build_index(ts_text)

    st.session_state.ctx = VideoContext(
        video_id=video_id,
        plain_transcript=plain,
        timestamped_transcript=ts_text,
        segments=segments,
        has_timestamps=bool(segments),
        summary=summary,
        chapters=chapters,
        rag_collection=rag_collection,
        use_rag=use_rag,
    )
    st.session_state.ready = True
    st.rerun()


def _render_manual_fallback() -> None:
    st.markdown(
        '<p style="font-size:.9rem;font-weight:600;color:var(--tx);margin:1.5rem 0 .5rem">'
        "Paste transcript manually</p>",
        unsafe_allow_html=True,
    )
    manual = st.text_area(
        "Manual transcript",
        height=200,
        placeholder="Paste the full transcript here...",
        label_visibility="collapsed",
        key="manual_text",
    )
    if st.button("Use this transcript", type="primary", key="use_manual"):
        if not manual.strip():
            st.error("Please paste some transcript text first.")
            return
        if not st.session_state.gemini_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            return

        with st.spinner("Analyzing transcript..."):
            summary = ai.generate_summary(
                st.session_state.gemini_key, manual.strip(), st.session_state.model_name
            )
        st.session_state.ctx = VideoContext(
            video_id="manual",
            plain_transcript=manual.strip(),
            timestamped_transcript=manual.strip(),
            segments=[],
            has_timestamps=False,
            summary=summary,
        )
        st.session_state.ready = True
        st.session_state.need_manual = False
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# CHAT PHASE — a video is loaded
# ═════════════════════════════════════════════════════════════════════════════
def render_chat_phase() -> None:
    ctx: VideoContext = st.session_state.ctx
    _render_video_card(ctx)
    _render_export_button(ctx)
    _render_metadata_tabs(ctx)
    st.markdown(
        "<hr style='border:none;border-top:1px solid var(--bds);margin:1.5rem 0'>",
        unsafe_allow_html=True,
    )
    _process_pending_question()
    _render_chat_history()
    _render_chat_input()


def _render_video_card(ctx: VideoContext) -> None:
    """The status card at the top of the chat view."""
    parts = [
        f'<span class="vcard-stat">{ctx.word_count:,} words</span>',
        f'<span class="vcard-stat">{len(ctx.chapters)} chapters</span>',
        f'<span class="vcard-stat">{st.session_state.model_name}</span>',
    ]
    if ctx.sentiment_done and ctx.sentiment.score >= 0:
        score = ctx.sentiment.score
        cls = "sent-pos" if score >= 60 else ("sent-neg" if score < 40 else "sent-mix")
        parts.append(
            f'<span class="sent-badge {cls}">{ctx.sentiment.label} · {score}%</span>'
        )
    if ctx.use_rag:
        parts.append('<span class="vcard-stat">🔍 RAG mode</span>')

    thumb = (
        f'<img class="vcard-thumb" src="{ctx.thumbnail_url}" alt="thumbnail" '
        f'onerror="this.style.display=\'none\'">'
        if ctx.thumbnail_url else '<div class="vcard-dot"></div>'
    )

    st.markdown(
        f'<div class="vcard">{thumb}'
        f'<div class="vcard-info"><h3>Video ready</h3><p>{"".join(parts)}</p></div></div>',
        unsafe_allow_html=True,
    )


def _render_export_button(ctx: VideoContext) -> None:
    if not st.session_state.chat_history:
        return
    lines = [
        f"# VideoMind export\n\nVideo: {ctx.video_id}\n",
        f"## Overview\n{ctx.summary}\n",
        "---\n",
    ]
    for turn in st.session_state.chat_history:
        role = "You" if turn["role"] == "user" else "VideoMind"
        lines.append(f"## {role}\n\n{turn['content']}\n\n---\n")
    st.download_button(
        "📥 Export chat (Markdown)",
        "\n".join(lines),
        f"videomind-{ctx.video_id}-{int(time.time())}.md",
        "text/markdown",
        key="export_btn",
    )


def _render_metadata_tabs(ctx: VideoContext) -> None:
    """Overview / Chapters / Transcript / Sentiment tabs."""
    tab_names: list[str] = []
    if ctx.summary: tab_names.append("📋 Overview")
    if ctx.chapters: tab_names.append("📑 Chapters")
    if ctx.segments or ctx.plain_transcript: tab_names.append("📝 Transcript")
    if not ctx.is_manual: tab_names.append("💬 Sentiment")
    if not tab_names:
        return

    tabs = iter(st.tabs(tab_names))

    if ctx.summary:
        with next(tabs):
            st.markdown(ctx.summary)

    if ctx.chapters:
        with next(tabs):
            for ch in ctx.chapters:
                st.markdown(
                    f'<div class="ch-item">'
                    f'<span class="ch-time">{html.escape(ch.time)}</span>'
                    f'<span class="ch-title">{html.escape(ch.title)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    if ctx.segments or ctx.plain_transcript:
        with next(tabs):
            if ctx.segments:
                lines = "\n".join(
                    f'<span class="t">[{s.time_str}]</span> {html.escape(s.text)}'
                    for s in ctx.segments
                )
                st.markdown(f'<div class="ts-viewer">{lines}</div>', unsafe_allow_html=True)
            else:
                st.text(ctx.plain_transcript[:8000])

    if not ctx.is_manual:
        with next(tabs):
            _render_sentiment_tab(ctx)


def _render_sentiment_tab(ctx: VideoContext) -> None:
    if ctx.sentiment_done:
        st.markdown(f"**{ctx.sentiment.label}** — {ctx.sentiment.score}/100")
        return

    st.caption(
        f"Analyse viewer sentiment from comments "
        f"(fetches up to {SENTIMENT_COMMENT_LIMIT})"
    )
    if st.button("Analyze sentiment", type="secondary", key="sent_btn"):
        if not st.session_state.gemini_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            return
        url = f"https://www.youtube.com/watch?v={ctx.video_id}"
        with st.spinner("Fetching comments & analysing..."):
            try:
                comments = youtube.fetch_comments(url, SENTIMENT_COMMENT_LIMIT)
                if not comments:
                    st.warning("No comments found for this video.")
                    return
                result = ai.analyze_sentiment(
                    st.session_state.gemini_key,
                    comments,
                    st.session_state.model_name,
                )
                ctx.sentiment = result
                ctx.sentiment_done = True
                st.rerun()
            except Exception as e:
                st.error(humanize_error(e))


def _process_pending_question() -> None:
    """If a suggestion chip queued a question, run it now."""
    pending = st.session_state.pending_q
    if not pending:
        return
    st.session_state.pending_q = ""
    if not st.session_state.gemini_key:
        st.session_state.chat_history.append({"role": "user", "content": pending})
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "__ERROR__:API key is required.",
        })
        return
    st.session_state.chat_history.append({"role": "user", "content": pending})
    _run_chat(pending)


def _render_chat_history() -> None:
    if not st.session_state.chat_history:
        _render_welcome_and_chips()
        return
    for turn in st.session_state.chat_history:
        if turn["role"] == "user":
            st.markdown(
                f'<div class="uq">{html.escape(turn["content"])}</div>',
                unsafe_allow_html=True,
            )
        else:
            content = turn["content"]
            is_error = content.startswith("__ERROR__:")
            if is_error:
                content = content.replace("__ERROR__:", "")
            err_cls = " err" if is_error else ""
            st.markdown(
                f'<div class="aa{err_cls}">{render_markdown(content)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="tsep"></div>', unsafe_allow_html=True)


def _render_welcome_and_chips() -> None:
    st.markdown(
        '<div class="welcome"><div class="welcome-icon">🎬</div>'
        "<p>Video analysed. Ask me anything about it.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, suggestion in enumerate(DEFAULT_SUGGESTIONS):
        with cols[i % 3]:
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state.pending_q = suggestion
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def _render_chat_input() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        col_q, col_b = st.columns([6, 1])
        with col_q:
            question = st.text_input(
                "Question",
                placeholder="Ask anything about the video...",
                label_visibility="collapsed",
            )
        with col_b:
            submitted = st.form_submit_button("→", type="primary", use_container_width=True)

    if submitted and question.strip():
        if not st.session_state.gemini_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            return
        st.session_state.chat_history.append({"role": "user", "content": question})
        st.markdown(
            f'<div class="uq">{html.escape(question)}</div>',
            unsafe_allow_html=True,
        )
        _run_chat(question)


def _run_chat(question: str) -> None:
    """Stream a response into the page and append it to history."""
    ctx: VideoContext = st.session_state.ctx
    api_key = st.session_state.gemini_key
    model = st.session_state.model_name

    # Build the transcript block — full text or RAG-retrieved chunks.
    if ctx.use_rag and ctx.rag_collection is not None:
        chunks = rag.retrieve(ctx.rag_collection, question, k=12)
        transcript_block = (
            "RELEVANT SECTIONS:\n" + "\n\n---\n\n".join(chunks)
            if chunks
            else f"FULL TRANSCRIPT (truncated):\n{ctx.timestamped_transcript[:50_000]}"
        )
    else:
        transcript_block = f"FULL TRANSCRIPT:\n{ctx.timestamped_transcript}"

    placeholder = st.empty()
    try:
        stream = ai.chat_stream(
            api_key=api_key,
            model_name=model,
            transcript_block=transcript_block,
            summary=ctx.summary,
            history=st.session_state.chat_history[:-1],  # exclude just-added user turn
            question=question,
            detail=st.session_state.detail_level,
            tone=st.session_state.tone_level,
            has_timestamps=ctx.has_timestamps,
        )
        final = stream_into_placeholder(placeholder, stream)
        st.session_state.chat_history.append({"role": "assistant", "content": final})
    except Exception as exc:
        msg = humanize_error(exc)
        placeholder.markdown(
            f'<div class="aa err">{html.escape(msg)}</div>',
            unsafe_allow_html=True,
        )
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"__ERROR__:{msg}",
        })


# ═════════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═════════════════════════════════════════════════════════════════════════════
if st.session_state.ready:
    render_chat_phase()
else:
    render_setup_phase()
