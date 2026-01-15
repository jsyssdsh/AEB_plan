"""
Retry management with exponential backoff.

Implements Principle 2: Recovery mechanisms through intelligent retry logic.
"""

import asyncio
import random
from typing import Callable, TypeVar

from llm_guardian.core.config import RetryConfig
from llm_guardian.core.exceptions import (
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    RetryExhaustedError,
)

T = TypeVar("T")


class RetryStrategy:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add jitter
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base**attempt), self.max_delay
        )

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class RetryManager:
    """
    Intelligent retry management for LLM requests.

    Implements exponential backoff with jitter to handle transient failures.
    """

    def __init__(self, config: RetryConfig):
        """
        Initialize retry manager.

        Args:
            config: Retry configuration
        """
        self.strategy = RetryStrategy(
            max_attempts=config.max_attempts,
            initial_delay=config.initial_delay_seconds,
            max_delay=config.max_delay_seconds,
            exponential_base=config.exponential_base,
            jitter=config.enable_jitter,
        )

        # Retryable error types
        self.retryable_errors = (
            ConnectionError,
            TimeoutError,
            LLMProviderTimeoutError,
            LLMProviderRateLimitError,
        )

    async def execute_with_retry(
        self, func: Callable[..., T], *args: any, **kwargs: any
    ) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retries exhausted
            Exception: Re-raises non-retryable exceptions
        """
        last_exception = None

        for attempt in range(self.strategy.max_attempts):
            try:
                result = await func(*args, **kwargs)

                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    print(
                        f"Request succeeded on attempt {attempt + 1}/{self.strategy.max_attempts}"
                    )

                return result

            except self.retryable_errors as e:
                last_exception = e

                if attempt < self.strategy.max_attempts - 1:
                    delay = self.strategy.get_delay(attempt)
                    print(
                        f"Request failed (attempt {attempt + 1}/{self.strategy.max_attempts}). "
                        f"Retrying in {delay:.2f}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    print(
                        f"Request failed after {self.strategy.max_attempts} attempts"
                    )

            except Exception as e:
                # Non-retryable error
                print(f"Non-retryable error encountered: {type(e).__name__}: {e}")
                raise

        # All retries exhausted
        raise RetryExhaustedError(
            f"Failed after {self.strategy.max_attempts} attempts",
            details={
                "max_attempts": self.strategy.max_attempts,
                "last_error": str(last_exception),
            },
        ) from last_exception
