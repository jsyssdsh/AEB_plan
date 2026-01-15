"""
Circuit breaker implementation for LLM API calls.

Implements Principle 2: Recovery mechanisms by preventing cascading failures
and enabling automatic recovery.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from llm_guardian.core.exceptions import CircuitBreakerOpenError

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking all requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for LLM API calls.

    State transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After recovery_timeout
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: timedelta = timedelta(seconds=60),
        success_threshold: int = 2,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            success_threshold: Number of successes needed to close from half-open
            expected_exception: Base exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.utcnow()

        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_history: list[tuple[CircuitState, datetime]] = [
            (CircuitState.CLOSED, self.last_state_change)
        ]

        # Thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Re-raises exceptions from function
        """
        async with self._lock:
            self.total_calls += 1

            # Check if we should transition to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. "
                        f"Retry after {self._time_until_retry():.1f}s",
                        details={
                            "state": self.state.value,
                            "failure_count": self.failure_count,
                            "last_failure_time": self.last_failure_time,
                            "time_until_retry": self._time_until_retry(),
                        },
                    )

        # Attempt the call (outside lock to avoid blocking)
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self.failure_count = 0
            self.total_successes += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    self.success_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.total_failures += 1
            self.last_failure_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN immediately opens circuit
                self._transition_to(CircuitState.OPEN)
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt reset.

        Returns:
            True if should attempt reset
        """
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() - self.last_failure_time >= self.recovery_timeout

    def _time_until_retry(self) -> float:
        """
        Calculate time until retry is allowed.

        Returns:
            Seconds until retry
        """
        if self.last_failure_time is None:
            return 0.0

        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        remaining = self.recovery_timeout.total_seconds() - elapsed
        return max(0.0, remaining)

    def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to new state.

        Args:
            new_state: State to transition to
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.last_state_change = datetime.utcnow()
            self.state_history.append((new_state, self.last_state_change))

            # Reset counters on state change
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.success_count = 0

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
            "time_until_retry": self._time_until_retry(),
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": (
                self.total_failures / self.total_calls if self.total_calls > 0 else 0.0
            ),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self.get_state()

        # Add state history summary
        stats["state_changes"] = len(self.state_history)
        stats["time_in_current_state"] = (
            datetime.utcnow() - self.last_state_change
        ).total_seconds()

        # Calculate time in each state
        state_times: Dict[str, float] = {
            CircuitState.CLOSED.value: 0.0,
            CircuitState.OPEN.value: 0.0,
            CircuitState.HALF_OPEN.value: 0.0,
        }

        for i in range(len(self.state_history) - 1):
            state, start_time = self.state_history[i]
            _, end_time = self.state_history[i + 1]
            duration = (end_time - start_time).total_seconds()
            state_times[state.value] += duration

        # Add current state duration
        current_state, start_time = self.state_history[-1]
        current_duration = (datetime.utcnow() - start_time).total_seconds()
        state_times[current_state.value] += current_duration

        stats["time_in_states"] = state_times

        return stats

    async def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        async with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None

    def is_available(self) -> bool:
        """
        Check if circuit breaker will allow calls.

        Returns:
            True if calls are allowed
        """
        if self.state == CircuitState.CLOSED or self.state == CircuitState.HALF_OPEN:
            return True
        elif self.state == CircuitState.OPEN:
            return self._should_attempt_reset()
        return False


class MultiCircuitBreaker:
    """
    Manage multiple circuit breakers for different services/providers.

    Useful for managing separate circuit breakers per LLM provider.
    """

    def __init__(
        self,
        default_failure_threshold: int = 5,
        default_recovery_timeout: timedelta = timedelta(seconds=60),
    ):
        """
        Initialize multi-circuit breaker.

        Args:
            default_failure_threshold: Default failure threshold
            default_recovery_timeout: Default recovery timeout
        """
        self.default_failure_threshold = default_failure_threshold
        self.default_recovery_timeout = default_recovery_timeout
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker by name.

        Args:
            name: Circuit breaker identifier (e.g., provider name)

        Returns:
            CircuitBreaker instance
        """
        async with self._lock:
            if name not in self.breakers:
                self.breakers[name] = CircuitBreaker(
                    failure_threshold=self.default_failure_threshold,
                    recovery_timeout=self.default_recovery_timeout,
                )
            return self.breakers[name]

    async def call(
        self, name: str, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute function with named circuit breaker.

        Args:
            name: Circuit breaker name
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        breaker = await self.get_breaker(name)
        return await breaker.call(func, *args, **kwargs)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get states of all circuit breakers.

        Returns:
            Dictionary mapping names to states
        """
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}

    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping names to statistics
        """
        return {name: breaker.get_statistics() for name, breaker in self.breakers.items()}
