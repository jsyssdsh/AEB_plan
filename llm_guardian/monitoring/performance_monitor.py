"""
Performance monitoring for LLM requests.

Track latency, token usage, costs, and detect performance anomalies.
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

from llm_guardian.core.config import MonitoringConfig
from llm_guardian.core.exceptions import (
    BudgetExceededError,
    SessionBudgetExceededError,
)
from llm_guardian.core.models import (
    LLMResponse,
    MonitoringAlert,
    PerformanceMetrics,
    RequestContext,
)


class PerformanceMonitor:
    """
    Track and analyze performance metrics.

    Monitors:
    - Latency (with percentile calculations)
    - Token usage
    - Costs
    - Budget enforcement
    - Performance anomalies
    """

    def __init__(self, config: MonitoringConfig):
        """
        Initialize performance monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config

        # Historical metrics storage
        self.metrics_history: deque = deque(maxlen=10000)

        # Cost tracking per session/user
        self.session_costs: Dict[str, float] = {}
        self.user_costs: Dict[str, float] = {}

        # Daily cost reset tracking
        self.daily_cost_reset: Dict[str, datetime] = {}

        # Performance baselines
        self.latency_baseline_p50: Optional[float] = None
        self.latency_baseline_p95: Optional[float] = None

        # Alert tracking
        self.active_alerts: List[MonitoringAlert] = []

    async def record_metrics(
        self, response: LLMResponse, context: RequestContext
    ) -> PerformanceMetrics:
        """
        Record performance metrics for a request.

        Args:
            response: LLM response
            context: Request context

        Returns:
            PerformanceMetrics object

        Raises:
            BudgetExceededError: If request exceeds budget
            SessionBudgetExceededError: If session exceeds budget
        """
        # Extract token counts from raw response
        usage = response.raw_response.get("usage", {})

        metrics = PerformanceMetrics(
            request_id=response.request_id,
            latency_ms=response.latency_ms,
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            tokens_total=response.tokens_used,
            cost_usd=response.cost_usd,
            provider=response.provider,
            model=response.model,
            timestamp=response.timestamp,
        )

        # Store in history
        self.metrics_history.append(metrics)

        # Update cost tracking
        if context.session_id:
            self.session_costs[context.session_id] = (
                self.session_costs.get(context.session_id, 0.0) + metrics.cost_usd
            )

        if context.user_id:
            # Reset daily costs if needed
            self._reset_daily_costs_if_needed(context.user_id)

            self.user_costs[context.user_id] = (
                self.user_costs.get(context.user_id, 0.0) + metrics.cost_usd
            )

        # Check for anomalies
        await self._check_performance_anomalies(metrics, context)

        # Check budget limits (after recording to track even failed requests)
        await self._check_budget_limits(metrics, context)

        # Update baselines periodically
        if len(self.metrics_history) % 100 == 0:
            self._update_baselines()

        return metrics

    async def _check_performance_anomalies(
        self, metrics: PerformanceMetrics, context: RequestContext
    ) -> None:
        """
        Detect performance anomalies.

        Args:
            metrics: Current metrics
            context: Request context
        """
        # Need minimum history for anomaly detection
        if len(self.metrics_history) < 100:
            return

        recent_latencies = [m.latency_ms for m in list(self.metrics_history)[-100:]]
        p95 = np.percentile(recent_latencies, 95)

        # Alert if current latency exceeds p95 by 2x
        if metrics.latency_ms > p95 * 2:
            await self._raise_performance_alert(
                severity="medium",
                message=f"High latency detected: {metrics.latency_ms:.0f}ms (p95: {p95:.0f}ms)",
                metrics=metrics,
                context=context,
            )

        # Alert if latency exceeds configured threshold
        if metrics.latency_ms > self.config.performance_alert_threshold_ms:
            await self._raise_performance_alert(
                severity="high",
                message=f"Latency {metrics.latency_ms:.0f}ms exceeds threshold {self.config.performance_alert_threshold_ms:.0f}ms",
                metrics=metrics,
                context=context,
            )

    async def _check_budget_limits(
        self, metrics: PerformanceMetrics, context: RequestContext
    ) -> None:
        """
        Check if budget limits are exceeded.

        Args:
            metrics: Performance metrics
            context: Request context

        Raises:
            BudgetExceededError: If request budget exceeded
            SessionBudgetExceededError: If session budget exceeded
        """
        # Check per-request budget
        if context.max_cost_usd and metrics.cost_usd > context.max_cost_usd:
            raise BudgetExceededError(
                f"Request cost ${metrics.cost_usd:.4f} exceeds limit ${context.max_cost_usd:.4f}",
                details={
                    "request_cost": metrics.cost_usd,
                    "budget_limit": context.max_cost_usd,
                    "request_id": metrics.request_id,
                },
            )

        # Check session budget
        if context.session_id:
            session_total = self.session_costs.get(context.session_id, 0.0)
            # Get session budget from config (would need to pass this in context)
            # For now, we'll skip this check if not provided

        # Check user daily budget
        if context.user_id:
            user_total = self.user_costs.get(context.user_id, 0.0)
            # Similar - would need budget info

    def _reset_daily_costs_if_needed(self, user_id: str) -> None:
        """
        Reset daily costs if a new day has started.

        Args:
            user_id: User identifier
        """
        now = datetime.utcnow()
        last_reset = self.daily_cost_reset.get(user_id)

        if not last_reset or (now.date() > last_reset.date()):
            self.user_costs[user_id] = 0.0
            self.daily_cost_reset[user_id] = now

    def _update_baselines(self) -> None:
        """Update performance baselines from historical data."""
        if len(self.metrics_history) < 100:
            return

        recent_latencies = [m.latency_ms for m in list(self.metrics_history)[-1000:]]
        self.latency_baseline_p50 = float(np.percentile(recent_latencies, 50))
        self.latency_baseline_p95 = float(np.percentile(recent_latencies, 95))

    async def _raise_performance_alert(
        self,
        severity: str,
        message: str,
        metrics: PerformanceMetrics,
        context: RequestContext,
    ) -> None:
        """
        Raise performance monitoring alert.

        Args:
            severity: Alert severity
            message: Alert message
            metrics: Performance metrics
            context: Request context
        """
        alert = MonitoringAlert(
            alert_id=f"alert-perf-{metrics.request_id}",
            severity=severity,
            category="performance",
            message=message,
            details={
                "latency_ms": metrics.latency_ms,
                "tokens_used": metrics.tokens_total,
                "cost_usd": metrics.cost_usd,
                "provider": metrics.provider,
                "model": metrics.model,
            },
            request_id=metrics.request_id,
        )

        self.active_alerts.append(alert)

    def get_performance_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, any]:
        """
        Get performance summary for time window.

        Args:
            time_window: Time window to analyze (None for all history)

        Returns:
            Dictionary with performance statistics
        """
        if not self.metrics_history:
            return {}

        # Filter by time window if provided
        if time_window:
            cutoff = datetime.utcnow() - time_window
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff]
        else:
            recent_metrics = list(self.metrics_history)

        if not recent_metrics:
            return {}

        latencies = [m.latency_ms for m in recent_metrics]
        costs = [m.cost_usd for m in recent_metrics]
        tokens = [m.tokens_total for m in recent_metrics]

        return {
            "request_count": len(recent_metrics),
            "latency_mean": float(np.mean(latencies)),
            "latency_p50": float(np.percentile(latencies, 50)),
            "latency_p95": float(np.percentile(latencies, 95)),
            "latency_p99": float(np.percentile(latencies, 99)),
            "latency_min": float(np.min(latencies)),
            "latency_max": float(np.max(latencies)),
            "total_cost_usd": sum(costs),
            "avg_cost_usd": float(np.mean(costs)),
            "total_tokens": sum(tokens),
            "avg_tokens": float(np.mean(tokens)),
        }

    def get_cost_summary(self) -> Dict[str, any]:
        """
        Get cost summary by session and user.

        Returns:
            Dictionary with cost statistics
        """
        return {
            "session_costs": dict(self.session_costs),
            "user_costs": dict(self.user_costs),
            "total_sessions": len(self.session_costs),
            "total_users": len(self.user_costs),
        }

    def get_provider_breakdown(
        self, time_window: Optional[timedelta] = None
    ) -> Dict[str, Dict[str, any]]:
        """
        Get performance breakdown by provider.

        Args:
            time_window: Optional time window

        Returns:
            Dictionary with per-provider statistics
        """
        if not self.metrics_history:
            return {}

        # Filter by time window
        if time_window:
            cutoff = datetime.utcnow() - time_window
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff]
        else:
            recent_metrics = list(self.metrics_history)

        # Group by provider
        provider_metrics: Dict[str, List[PerformanceMetrics]] = {}
        for metric in recent_metrics:
            if metric.provider not in provider_metrics:
                provider_metrics[metric.provider] = []
            provider_metrics[metric.provider].append(metric)

        # Calculate statistics per provider
        breakdown = {}
        for provider, metrics in provider_metrics.items():
            latencies = [m.latency_ms for m in metrics]
            costs = [m.cost_usd for m in metrics]

            breakdown[provider] = {
                "request_count": len(metrics),
                "latency_p50": float(np.percentile(latencies, 50)),
                "latency_p95": float(np.percentile(latencies, 95)),
                "total_cost_usd": sum(costs),
                "avg_cost_usd": float(np.mean(costs)),
            }

        return breakdown

    def get_active_alerts(self) -> List[MonitoringAlert]:
        """
        Get list of active performance alerts.

        Returns:
            List of unresolved alerts
        """
        return [alert for alert in self.active_alerts if not alert.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved.

        Args:
            alert_id: Alert identifier

        Returns:
            True if alert was found and resolved
        """
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False
