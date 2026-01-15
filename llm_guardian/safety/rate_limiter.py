"""
Rate limiting implementation for LLM requests.

Implements multi-level rate limiting to prevent resource exhaustion and enforce quotas.
"""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional

from llm_guardian.core.config import RateLimitConfig
from llm_guardian.core.exceptions import QuotaExceededError, RateLimitExceededError
from llm_guardian.core.models import RequestContext


class TokenBucket:
    """
    Token bucket algorithm for smooth rate limiting.

    Tokens are replenished at a constant rate. Each request consumes tokens.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_for_tokens(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Wait for tokens to become available.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum wait time in seconds

        Returns:
            True if tokens were acquired within timeout

        Raises:
            RateLimitExceededError: If timeout expires
        """
        start_time = datetime.utcnow()

        while True:
            if await self.acquire(tokens):
                return True

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout:
                raise RateLimitExceededError(
                    f"Rate limit: could not acquire {tokens} tokens within {timeout}s timeout",
                    details={
                        "requested_tokens": tokens,
                        "available_tokens": self.tokens,
                        "timeout_seconds": timeout,
                    },
                )

            # Wait a bit before retrying
            await asyncio.sleep(0.1)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        elapsed = (now - self.last_refill).total_seconds()
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_available_tokens(self) -> float:
        """
        Get number of available tokens.

        Returns:
            Available tokens
        """
        # Refill before returning
        now = datetime.utcnow()
        elapsed = (now - self.last_refill).total_seconds()
        tokens_to_add = elapsed * self.refill_rate
        return min(self.capacity, self.tokens + tokens_to_add)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter for precise control.

    Maintains a window of recent requests and enforces limits.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: deque = deque()
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            user_id: User identifier

        Returns:
            True if within rate limit

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Remove old requests
            while self.requests and self.requests[0][1] < cutoff:
                self.requests.popleft()

            # Count requests for this user
            user_requests = sum(1 for uid, _ in self.requests if uid == user_id)

            if user_requests >= self.max_requests:
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {user_requests}/{self.max_requests} requests in {self.window.total_seconds()}s window",
                    details={
                        "user_id": user_id,
                        "requests_in_window": user_requests,
                        "max_requests": self.max_requests,
                        "window_seconds": self.window.total_seconds(),
                    },
                )

            # Add this request
            self.requests.append((user_id, now))
            return True


class RateLimiter:
    """
    Multi-level rate limiting with quota management.

    Implements:
    - Global rate limiting
    - Per-user rate limiting
    - Cost-based quota tracking
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config

        # Global rate limiter (token bucket for smooth limiting)
        self.global_limiter = TokenBucket(
            capacity=config.global_max_requests_per_minute,
            refill_rate=config.global_max_requests_per_minute / 60.0,
        )

        # Per-user rate limiters (created on demand)
        self.user_limiters: Dict[str, TokenBucket] = {}

        # Cost-based quota tracking
        self.user_quotas: Dict[str, float] = {}
        self.user_quota_reset: Dict[str, datetime] = {}
        self.session_costs: Dict[str, float] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def check_limits(self, context: RequestContext) -> None:
        """
        Check all rate limits before allowing request.

        Args:
            context: Request context

        Raises:
            RateLimitExceededError: If rate limit exceeded
            QuotaExceededError: If quota exceeded
        """
        # 1. Check global rate limit
        if not await self.global_limiter.acquire():
            raise RateLimitExceededError(
                "Global rate limit exceeded",
                details={
                    "global_limit": self.config.global_max_requests_per_minute,
                    "period": "per minute",
                },
            )

        # 2. Check per-user rate limit
        if context.user_id:
            user_limiter = await self._get_user_limiter(context.user_id)
            if not await user_limiter.acquire():
                raise RateLimitExceededError(
                    f"User rate limit exceeded for {context.user_id}",
                    details={
                        "user_id": context.user_id,
                        "user_limit": self.config.user_max_requests_per_minute,
                        "period": "per minute",
                    },
                )

        # 3. Check user daily quota (cost-based)
        if context.user_id and self.config.user_daily_quota_usd is not None:
            await self._check_user_quota(context.user_id, self.config.user_daily_quota_usd)

        # 4. Check session budget
        if context.session_id and self.config.session_budget_usd is not None:
            await self._check_session_budget(
                context.session_id, self.config.session_budget_usd
            )

    async def record_cost(self, context: RequestContext, cost_usd: float) -> None:
        """
        Record cost for quota tracking.

        Args:
            context: Request context
            cost_usd: Cost in USD
        """
        async with self._lock:
            # Update user quota
            if context.user_id:
                self._reset_user_quota_if_needed(context.user_id)
                self.user_quotas[context.user_id] = (
                    self.user_quotas.get(context.user_id, 0.0) + cost_usd
                )

            # Update session cost
            if context.session_id:
                self.session_costs[context.session_id] = (
                    self.session_costs.get(context.session_id, 0.0) + cost_usd
                )

    async def _get_user_limiter(self, user_id: str) -> TokenBucket:
        """
        Get or create user-specific rate limiter.

        Args:
            user_id: User identifier

        Returns:
            TokenBucket for user
        """
        async with self._lock:
            if user_id not in self.user_limiters:
                self.user_limiters[user_id] = TokenBucket(
                    capacity=self.config.user_max_requests_per_minute,
                    refill_rate=self.config.user_max_requests_per_minute / 60.0,
                )
            return self.user_limiters[user_id]

    async def _check_user_quota(self, user_id: str, daily_quota_usd: float) -> None:
        """
        Check user daily quota.

        Args:
            user_id: User identifier
            daily_quota_usd: Daily quota in USD

        Raises:
            QuotaExceededError: If quota exceeded
        """
        async with self._lock:
            self._reset_user_quota_if_needed(user_id)

            current_quota = self.user_quotas.get(user_id, 0.0)
            if current_quota >= daily_quota_usd:
                raise QuotaExceededError(
                    f"Daily quota exceeded for user {user_id}: ${current_quota:.2f}/${daily_quota_usd:.2f}",
                    details={
                        "user_id": user_id,
                        "current_usage_usd": current_quota,
                        "daily_quota_usd": daily_quota_usd,
                    },
                )

    async def _check_session_budget(self, session_id: str, budget_usd: float) -> None:
        """
        Check session budget.

        Args:
            session_id: Session identifier
            budget_usd: Session budget in USD

        Raises:
            QuotaExceededError: If budget exceeded
        """
        async with self._lock:
            current_cost = self.session_costs.get(session_id, 0.0)
            if current_cost >= budget_usd:
                raise QuotaExceededError(
                    f"Session budget exceeded: ${current_cost:.2f}/${budget_usd:.2f}",
                    details={
                        "session_id": session_id,
                        "current_cost_usd": current_cost,
                        "budget_usd": budget_usd,
                    },
                )

    def _reset_user_quota_if_needed(self, user_id: str) -> None:
        """
        Reset user quota if a new day has started.

        Args:
            user_id: User identifier
        """
        now = datetime.utcnow()
        last_reset = self.user_quota_reset.get(user_id)

        if not last_reset or (now.date() > last_reset.date()):
            self.user_quotas[user_id] = 0.0
            self.user_quota_reset[user_id] = now

    def get_user_quota_status(self, user_id: str) -> Dict[str, any]:
        """
        Get user quota status.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with quota information
        """
        self._reset_user_quota_if_needed(user_id)

        current_usage = self.user_quotas.get(user_id, 0.0)
        daily_limit = self.config.user_daily_quota_usd or 0.0

        return {
            "user_id": user_id,
            "current_usage_usd": current_usage,
            "daily_limit_usd": daily_limit,
            "remaining_usd": max(0.0, daily_limit - current_usage),
            "usage_percentage": (current_usage / daily_limit * 100) if daily_limit > 0 else 0.0,
            "last_reset": self.user_quota_reset.get(user_id),
        }

    def get_session_budget_status(self, session_id: str) -> Dict[str, any]:
        """
        Get session budget status.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with budget information
        """
        current_cost = self.session_costs.get(session_id, 0.0)
        budget = self.config.session_budget_usd or 0.0

        return {
            "session_id": session_id,
            "current_cost_usd": current_cost,
            "budget_usd": budget,
            "remaining_usd": max(0.0, budget - current_cost),
            "usage_percentage": (current_cost / budget * 100) if budget > 0 else 0.0,
        }

    def get_global_status(self) -> Dict[str, any]:
        """
        Get global rate limiter status.

        Returns:
            Dictionary with global status
        """
        return {
            "available_tokens": self.global_limiter.get_available_tokens(),
            "capacity": self.global_limiter.capacity,
            "refill_rate_per_second": self.global_limiter.refill_rate,
        }
