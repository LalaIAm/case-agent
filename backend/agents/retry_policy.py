"""
Configurable retry policies: exponential backoff, jitter, retryable checks, circuit breaker.
"""
import asyncio
import logging
import random
from typing import Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exception types that are typically retryable (transient)
RETRYABLE_EXCEPTIONS = (asyncio.TimeoutError, ConnectionError, OSError)

# Base delay in seconds; backoff is base * 2^attempt + jitter
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_JITTER_FRACTION = 0.2


def is_retryable(e: Exception) -> bool:
    """Return True if the exception is considered retryable."""
    if isinstance(e, RETRYABLE_EXCEPTIONS):
        return True
    # OpenAI rate limit / temporary errors
    msg = str(e).lower()
    if "rate" in msg or "timeout" in msg or "temporarily" in msg or "overloaded" in msg:
        return True
    return False


def backoff_delay(attempt: int, base: float = DEFAULT_BASE_DELAY, max_delay: float = DEFAULT_MAX_DELAY, jitter: float = DEFAULT_JITTER_FRACTION) -> float:
    """Compute delay in seconds for this attempt (exponential backoff + jitter)."""
    delay = min(base * (2 ** attempt), max_delay)
    jitter_amount = delay * jitter * (2 * random.random() - 1)
    return max(0, delay + jitter_amount)


async def with_retries(
    coro_factory: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = DEFAULT_BASE_DELAY,
    retry_check: Callable[[Exception], bool] = is_retryable,
) -> T:
    """
    Execute the coroutine from factory; on retryable failure wait with backoff and retry.
    Raises the last exception if all attempts fail.
    """
    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            coro = coro_factory()
            return await coro  # type: ignore[misc]
        except Exception as e:
            last_error = e
            if attempt == max_attempts - 1 or not retry_check(e):
                raise
            delay = backoff_delay(attempt, base=base_delay)
            logger.warning("Attempt %s failed (%s), retrying in %.1fs: %s", attempt + 1, type(e).__name__, delay, e)
            await asyncio.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("with_retries: no result and no error")
