"""Retrieval-augmented generation for transcripts that exceed the model's
sweet spot.

For most videos we send the whole transcript to Gemini — it has a 1M-token
window and the snippets are small. But for multi-hour videos or unusually
verbose ones, we chunk the transcript, index it in an in-memory ChromaDB
collection, and retrieve the most relevant chunks per question.

The threshold is in `config.FULL_TRANSCRIPT_LIMIT`.
"""

from __future__ import annotations

import chromadb

# Each chunk is roughly this many characters. ~700 chars ≈ 150-180 tokens,
# small enough that 12 chunks fit comfortably in any prompt budget.
CHUNK_SIZE = 700
CHUNK_OVERLAP_LINES = 2


def _chunk_transcript(timestamped_transcript: str) -> list[str]:
    """Split a transcript into overlapping chunks suited for retrieval."""
    if not timestamped_transcript.strip():
        return ["(empty transcript)"]

    chunks: list[str] = []
    buffer: list[str] = []
    current_size = 0

    for line in timestamped_transcript.split("\n"):
        buffer.append(line)
        current_size += len(line)
        if current_size >= CHUNK_SIZE:
            chunks.append("\n".join(buffer))
            # Keep a small overlap so semantic boundaries don't sever context.
            buffer = buffer[-CHUNK_OVERLAP_LINES:]
            current_size = sum(len(line) for line in buffer)

    if buffer:
        chunks.append("\n".join(buffer))

    return chunks or ["(empty transcript)"]


def build_index(timestamped_transcript: str):
    """Build a fresh in-memory ChromaDB collection. Returns the collection."""
    if not timestamped_transcript or not timestamped_transcript.strip():
        raise ValueError("Cannot build an index from an empty transcript.")

    chunks = _chunk_transcript(timestamped_transcript)
    # A unique collection name per index keeps reruns isolated.
    client = chromadb.Client()
    collection_name = f"vid_ctx_{abs(hash(timestamped_transcript)) % (10**10)}"
    collection = client.get_or_create_collection(name=collection_name)

    # If the collection already exists from a previous identical input, skip add.
    if collection.count() == 0:
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(ids=ids, documents=chunks)

    return collection


def retrieve(collection, query: str, k: int = 12) -> list[str]:
    """Return the k most relevant chunks for `query`, or [] on any failure."""
    if not collection:
        return []
    try:
        n = min(k, collection.count())
        if n == 0:
            return []
        result = collection.query(query_texts=[query], n_results=n)
        return result.get("documents", [[]])[0]
    except Exception:
        return []
