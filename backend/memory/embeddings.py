"""
OpenAI embedding generation service for memory block vectorization.
"""
import asyncio
import functools
from typing import List

from openai import OpenAI

from backend.config import get_settings

# Approximate token limit for text-embedding-3-small (8191 max, use 8000 to be safe)
MAX_INPUT_TOKENS = 8000
# Rough chars per token for truncation
CHARS_PER_TOKEN = 4


@functools.lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    """Return a cached OpenAI client instance (singleton)."""
    settings = get_settings()
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _preprocess_text(text: str) -> str:
    """Strip whitespace and truncate to token limits."""
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    if not text:
        return ""
    max_chars = MAX_INPUT_TOKENS * CHARS_PER_TOKEN
    if len(text) > max_chars:
        return text[:max_chars]
    return text


class EmbeddingService:
    """Service for generating embeddings via OpenAI text-embedding-3-small."""

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self) -> None:
        self._client = _get_openai_client()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding for the given text.
        Uses exponential backoff retry on API failures.
        """
        processed = _preprocess_text(text)
        if not processed:
            raise ValueError("Cannot embed empty or invalid text")

        max_retries = 3
        base_delay = 1.0
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                # Run sync client in thread pool to avoid blocking
                def _create() -> List[float]:
                    resp = self._client.embeddings.create(
                        model=self.EMBEDDING_MODEL,
                        input=processed,
                    )
                    return resp.data[0].embedding

                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, _create)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise last_error from e

        raise last_error or RuntimeError("Embedding generation failed")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (more efficient).
        Empty or invalid texts get a zero vector so returned list length matches input.
        """
        if not texts:
            return []

        processed: List[str] = []
        indices: List[int] = []
        for i, t in enumerate(texts):
            p = _preprocess_text(t)
            if p:
                processed.append(p)
                indices.append(i)

        zero_vec = [0.0] * self.EMBEDDING_DIMENSIONS
        results: List[List[float]] = [zero_vec[:] for _ in texts]

        if not processed:
            return results

        # OpenAI allows batch input; max 2048 inputs per request, keep batch size reasonable
        batch_size = 100
        for start in range(0, len(processed), batch_size):
            batch = processed[start : start + batch_size]
            batch_indices = indices[start : start + batch_size]
            max_retries = 3
            base_delay = 1.0
            last_error: Exception | None = None

            for attempt in range(max_retries):
                try:
                    def _create_batch() -> List[List[float]]:
                        resp = self._client.embeddings.create(
                            model=self.EMBEDDING_MODEL,
                            input=batch,
                        )
                        ordered = [None] * len(batch)
                        for d in resp.data:
                            if d.index is not None and d.index < len(ordered):
                                ordered[d.index] = d.embedding
                        return [e if e is not None else zero_vec[:] for e in ordered]

                    loop = asyncio.get_event_loop()
                    embeddings = await loop.run_in_executor(None, _create_batch)
                    for idx, emb in zip(batch_indices, embeddings):
                        results[idx] = emb
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        await asyncio.sleep(delay)
                    else:
                        raise last_error from e

        return results
