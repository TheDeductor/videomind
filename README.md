# VideoMind 🎬

**Chat with any YouTube video using AI.** Paste a URL, get a transcript-grounded chatbot that cites timestamps, detects chapters, summarises the video, and analyses comment sentiment.

Built with Streamlit + Google Gemini, with an automatic RAG fallback (ChromaDB) for long videos.

---

## ✨ Features

- **Transcript-grounded chat** — every answer is anchored to the actual transcript, with timestamps like `[02:35]`.
- **Auto-detected chapters** — Gemini parses the timestamped transcript and proposes chapter markers.
- **Automatic summary** — a 2-3 sentence overview generated on load.
- **Comment sentiment analysis** — fetches up to 200 comments and produces a single sentiment score.
- **RAG fallback for long videos** — for transcripts over ~80k characters, an in-memory ChromaDB index retrieves the most relevant chunks per question.
- **Streaming responses** — answers stream into the UI as they're generated.
- **Dark and light themes** — fully styled, with a contrast pass that survives Streamlit's quirks.
- **Manual transcript paste** — when YouTube doesn't have captions, you can paste your own.
- **Export to Markdown** — save the full chat session as a `.md` file.
- **`.env` API key support** — set `GEMINI_API_KEY` once, never type it again.

---

## 🚀 Quick start

### 1. Clone

```bash
git clone https://github.com/<your-username>/videomind.git
cd videomind
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows PowerShell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey), then:

```bash
cp .env.example .env
# Edit .env and paste your key
```

Or paste it into the sidebar when the app loads (it persists for the session).

### 5. Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

---

## 🧠 How it works (technical)

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   User pastes   │───▶│  Extract video   │───▶│  Fetch transcript │
│   YouTube URL   │    │       ID (regex) │    │  (youtube-trans- │
└─────────────────┘    └──────────────────┘    │   cript-api)      │
                                               └─────────┬────────┘
                                                         │
                       ┌─────────────────────────────────┘
                       ▼
            ┌─────────────────────┐
            │  len(transcript)?   │
            └──────┬──────────┬───┘
                   │          │
            ≤ 80k chars   > 80k chars
                   │          │
                   ▼          ▼
       ┌───────────────┐  ┌──────────────────┐
       │ Send full     │  │ Chunk + index    │
       │ transcript    │  │ in ChromaDB,     │
       │ to Gemini     │  │ retrieve top-k   │
       └───────┬───────┘  │ per question     │
               │          └────────┬─────────┘
               │                   │
               └─────────┬─────────┘
                         ▼
             ┌───────────────────────┐
             │  Gemini generates     │
             │  streaming response   │
             │  with [timestamp]     │
             │  citations            │
             └───────────────────────┘
```

### Component breakdown

| File | Responsibility |
|---|---|
| `app.py` | Streamlit entry point. Owns session state, sidebar, view dispatch (setup vs chat). No AI or HTTP logic. |
| `videomind/models.py` | Typed dataclasses + enums. `VideoContext` is the central state object. |
| `videomind/youtube.py` | URL parsing, transcript fetching with language fallbacks, comment fetching. Pure functions — no Streamlit. |
| `videomind/ai.py` | All Gemini calls: summary, chapters, sentiment, streaming chat. Takes API key explicitly. |
| `videomind/rag.py` | ChromaDB-based chunking and retrieval. Built only when a transcript exceeds `FULL_TRANSCRIPT_LIMIT`. |
| `videomind/prompts.py` | All prompt templates. Pulling these out makes them easy to tune without grep-spelunking. |
| `videomind/theme.py` | Palette + CSS template. Generates a fresh stylesheet on each theme toggle. |
| `videomind/config.py` | Constants: model list, cache TTL, thresholds. |

### Key design decisions

1. **Pure modules, Streamlit at the edges.** `ai.py`, `youtube.py`, and `rag.py` know nothing about Streamlit. They take inputs, return outputs. This makes them testable and reusable.

2. **`VideoContext` as the single source of truth.** Once a video is loaded, everything the app needs lives on one dataclass in `st.session_state.ctx`. No scattered "is this loaded?" / "what model?" flags.

3. **System instruction sent once.** Gemini's `system_instruction` parameter is configured at model creation, so the multi-thousand-character ruleset isn't re-sent on every turn.

4. **Streaming over polling.** `model.generate_content(prompt, stream=True)` returns a generator. We `yield` chunks into a placeholder, so users see partial answers in real time.

5. **Question-shape heuristics.** Before sending the prompt, we check for words like "topics", "list", "summary" and prepend an explicit instruction ("scan the entire transcript"). This catches a failure mode where Gemini stops after finding a few items.

6. **RAG threshold = 80k chars.** Below that, Gemini's 1M-token context comfortably swallows the whole transcript and gives better answers than retrieval. Above that, retrieval is cheaper and faster.

7. **In-memory ChromaDB.** No persistence — the index lives for the session. Simpler ops, faster cold starts, no disk hygiene.

8. **Caching.** `@st.cache_data(ttl=24h)` on transcript fetches means re-runs of the same video are instant.

---



## ⚙️ Configuration

All tunables live in `videomind/config.py`:

| Constant | Default | What it controls |
|---|---|---|
| `FULL_TRANSCRIPT_LIMIT` | `80_000` | Char threshold for switching to RAG mode |
| `AVAILABLE_MODELS` | 4 Gemini models | Sidebar model selector |
| `DEFAULT_MODEL` | `gemini-2.5-flash` | Initial model |
| `SENTIMENT_COMMENT_LIMIT` | `200` | Max comments fetched for sentiment |
| `TRANSCRIPT_CACHE_TTL` | `86400` (24h) | How long Streamlit caches transcript fetches |
| `DEFAULT_SUGGESTIONS` | 6 prompts | Suggestion chips on empty chat |

---

## 🐛 Known limitations

- **Comment download is unofficial.** `youtube-comment-downloader` scrapes the public page; YouTube can change markup and break it.
- **Auto-generated transcripts are noisy.** If captions are auto-translated or auto-generated, expect rough phrasing.
- **Rate limits.** The free Gemini tier has per-minute and per-day caps. On `gemini-2.5-flash`, a long transcript + chapter detect + summary call can use ~30k tokens in one analysis pass.
- **No persistent chat history.** The session resets when you close the tab. By design — add Streamlit's `st.cache_resource` keyed on `video_id` if you want it.

---

## 📦 Project structure

```
videomind/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── videomind/
    ├── __init__.py
    ├── ai.py               # Gemini calls
    ├── config.py           # Constants
    ├── models.py           # Dataclasses, enums
    ├── prompts.py          # Prompt templates
    ├── rag.py              # ChromaDB indexing/retrieval
    ├── theme.py            # CSS + colour palette
    └── youtube.py          # Transcript & comment fetching
```

---

## 🛣 Roadmap ideas

- **Migrate to the `google-genai` SDK.** The current code uses `google-generativeai`, which Google has deprecated in favour of `google-genai`. The shim still works but emits a `FutureWarning`. A migration is straightforward — change one import and a couple of method names.
- Persist chat history to `st.cache_resource` keyed on `video_id`.
- Add a "play at timestamp" link — clicking `[02:35]` in an answer opens the video at that point.
- Multi-video chat: load several videos into one context for comparison.
- Whisper-based transcript fallback when YouTube has no captions.
- Self-hosted local model option (Ollama/llama.cpp) for fully offline use.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io) for the UI framework.
- [Google Gemini](https://ai.google.dev) for the language model.
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) and [youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader) for the YouTube data layer.
- [ChromaDB](https://www.trychroma.com) for in-memory vector search.
