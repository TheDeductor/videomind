"""Configuration constants.

Pulling these out of business logic makes them tunable without grep-spelunking.
"""

# Below this transcript size we send the whole thing to the model.
# Above it, we build a ChromaDB index and retrieve the relevant chunks per query.
# Gemini 2.5 Flash has a 1M-token window; 80k chars ≈ 20k tokens — comfortably safe.
FULL_TRANSCRIPT_LIMIT = 80_000

# Models that we expose in the sidebar selector.
AVAILABLE_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)
DEFAULT_MODEL = "gemini-2.5-flash"

# How many comments we fetch when the user runs sentiment analysis.
SENTIMENT_COMMENT_LIMIT = 200

# Cache TTL for transcript fetches (seconds). Long because YouTube transcripts
# almost never change after a video is published.
TRANSCRIPT_CACHE_TTL = 60 * 60 * 24  # 24 hours

# Default suggestion chips shown on the empty chat screen.
DEFAULT_SUGGESTIONS = (
    "Summarize the video",
    "What topics are covered?",
    "Key takeaways",
    "Explain the main concept",
    "What's the conclusion?",
    "List all definitions mentioned",
)
