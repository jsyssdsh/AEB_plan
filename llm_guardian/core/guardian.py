"""
Main LLM Guardian orchestrator.

Coordinates all monitoring, safety, and recovery components to provide
comprehensive protection for LLM applications.

Implements all three core principles:
1. Monitoring as early warning
2. Recovery mechanisms
3. Fundamental design quality
"""

from datetime import timedelta
from typing import Dict, Optional

from llm_guardian.core.config import GuardianConfig
from llm_guardian.core.exceptions import (
    MissingAPIKeyError,
    UnsupportedProviderError,
    ValidationError,
)
from llm_guardian.core.models import LLMResponse, RequestContext, ResponseQuality
from llm_guardian.integrations.anthropic_client import AnthropicClient
from llm_guardian.integrations.base import BaseLLMClient
from llm_guardian.integrations.openai_client import OpenAIClient
from llm_guardian.monitoring.performance_monitor import PerformanceMonitor
from llm_guardian.monitoring.quality_monitor import QualityMonitor
from llm_guardian.recovery.audit_logger import AuditLogger
from llm_guardian.recovery.retry_manager import RetryManager
from llm_guardian.recovery.state_manager import StateManager
from llm_guardian.safety.circuit_breaker import CircuitBreaker
from llm_guardian.safety.rate_limiter import RateLimiter
from llm_guardian.safety.validators import InputValidator, OutputValidator


class LLMGuardian:
    """
    Main orchestrator for LLM monitoring and safety.

    Provides comprehensive protection through:
    - Quality and performance monitoring (Principle 1)
    - Circuit breakers and retry logic (Principle 2)
    - Input/output validation (Principle 3)
    - Audit logging and recovery
    """

    def __init__(self, config: GuardianConfig):
        """
        Initialize LLM Guardian.

        Args:
            config: Guardian configuration

        Raises:
            MissingAPIKeyError: If no API keys configured
        """
        self.config = config

        # Validate configuration
        if config.enable_safety_checks:
            config.validate_required_keys()

        # Initialize monitoring components (Principle 1)
        self.quality_monitor = QualityMonitor(config.monitoring)
        self.performance_monitor = PerformanceMonitor(config.monitoring)

        # Initialize safety mechanisms (Principle 2)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.safety.circuit_breaker_threshold,
            recovery_timeout=timedelta(seconds=config.safety.circuit_recovery_seconds),
        )
        self.rate_limiter = RateLimiter(config.rate_limiting)

        # Initialize validators (Principle 3)
        self.input_validator = InputValidator(config.safety)
        self.output_validator = OutputValidator(config.safety)

        # Initialize recovery systems (Principle 2)
        self.retry_manager = RetryManager(config.retry_strategy)
        self.state_manager = StateManager(config.state_storage_path)
        self.audit_logger = AuditLogger(config.audit_log_path)

        # LLM client adapters
        self.llm_clients: Dict[str, BaseLLMClient] = {}
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize LLM provider clients."""
        if self.config.anthropic_api_key:
            self.llm_clients["anthropic"] = AnthropicClient(self.config.anthropic_api_key)

        if self.config.openai_api_key:
            self.llm_clients["openai"] = OpenAIClient(self.config.openai_api_key)

    async def execute_request(
        self,
        context: RequestContext,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
    ) -> LLMResponse:
        """
        Execute LLM request with comprehensive monitoring and safety.

        This orchestrates all safety and monitoring mechanisms:
        1. Audit logging
        2. Input validation (Principle 3)
        3. Rate limiting
        4. State checkpointing
        5. Circuit breaker + retry (Principle 2)
        6. Quality monitoring (Principle 1)
        7. Performance monitoring
        8. Output validation (Principle 3)

        Args:
            context: Request context
            provider: LLM provider ("anthropic" or "openai")
            model: Model identifier

        Returns:
            LLMResponse with monitoring metadata

        Raises:
            ValidationError: If validation fails
            RateLimitExceededError: If rate limit exceeded
            QuotaExceededError: If quota exceeded
            CircuitBreakerOpenError: If circuit breaker is open
            Exception: Other errors from LLM providers
        """
        # 1. Audit logging - log incoming request
        self.audit_logger.log_request(context)

        try:
            # 2. Input validation (Principle 3: Validation at boundaries)
            if self.config.enable_safety_checks:
                await self.input_validator.validate_input(context)

            # 3. Rate limiting check
            await self.rate_limiter.check_limits(context)

            # 4. Save checkpoint for recovery
            if self.config.enable_recovery:
                await self.state_manager.save_checkpoint(
                    context.request_id, context, {"stage": "pre_execution"}
                )

            # 5. Execute with circuit breaker and retry (Principle 2: Recovery)
            try:
                response = await self.circuit_breaker.call(
                    self._execute_with_retry, context, provider, model
                )
            except Exception as e:
                self.audit_logger.log_error(
                    context.request_id, e, {"provider": provider, "model": model}
                )

                # Attempt graceful degradation
                if self.config.fallback_provider and provider != self.config.fallback_provider:
                    response = await self._handle_failure_with_fallback(context, e)
                else:
                    raise

            # 6. Quality monitoring (Principle 1: Early warning)
            if self.config.enable_monitoring:
                await self.quality_monitor.assess_quality(response, context)

            # 7. Performance monitoring
            if self.config.enable_monitoring:
                metrics = await self.performance_monitor.record_metrics(response, context)

                # Record cost for quota tracking
                await self.rate_limiter.record_cost(context, metrics.cost_usd)

            # 8. Output validation (Principle 3: Validation at boundaries)
            if self.config.enable_safety_checks:
                validation_result = await self.output_validator.validate_output(response)
                if not validation_result.is_valid:
                    # Log validation failure
                    self.audit_logger.log_error(
                        context.request_id,
                        ValidationError(
                            f"Output validation failed: {validation_result.errors}"
                        ),
                        {"validation_result": validation_result.model_dump()},
                    )

                    # For critical failures, attempt fallback or reject
                    if validation_result.severity == "critical":
                        if self.config.fallback_provider:
                            response = await self._handle_failure_with_fallback(
                                context, ValidationError("Critical validation failure")
                            )
                        else:
                            raise ValidationError(
                                "Output validation failed",
                                details={"errors": validation_result.errors},
                            )

            # 9. Audit logging - log successful response
            self.audit_logger.log_response(response)

            # 10. Update checkpoint
            if self.config.enable_recovery:
                await self.state_manager.save_checkpoint(
                    context.request_id,
                    context,
                    {"stage": "completed", "response_id": response.request_id},
                )

            return response

        except Exception as e:
            # Log all errors
            self.audit_logger.log_error(context.request_id, e)
            raise

    async def _execute_with_retry(
        self, context: RequestContext, provider: str, model: str
    ) -> LLMResponse:
        """
        Execute with retry logic.

        Args:
            context: Request context
            provider: LLM provider
            model: Model identifier

        Returns:
            LLMResponse
        """

        async def _call_llm() -> LLMResponse:
            client = self._get_llm_client(provider)
            return await client.generate(context, model)

        return await self.retry_manager.execute_with_retry(_call_llm)

    async def _handle_failure_with_fallback(
        self, context: RequestContext, error: Exception
    ) -> LLMResponse:
        """
        Handle execution failure with graceful degradation to fallback provider.

        Args:
            context: Request context
            error: Original error

        Returns:
            LLMResponse from fallback provider

        Raises:
            Exception: If fallback also fails
        """
        if not self.config.fallback_provider:
            raise error

        try:
            return await self._execute_with_retry(
                context, self.config.fallback_provider, self.config.fallback_model or "gpt-3.5-turbo"
            )
        except Exception as fallback_error:
            self.audit_logger.log_error(
                context.request_id,
                fallback_error,
                {"fallback_attempted": True, "original_error": str(error)},
            )
            raise error from fallback_error

    def _get_llm_client(self, provider: str) -> BaseLLMClient:
        """
        Get LLM client for provider.

        Args:
            provider: Provider name

        Returns:
            BaseLLMClient instance

        Raises:
            UnsupportedProviderError: If provider not supported or configured
        """
        if provider not in self.llm_clients:
            raise UnsupportedProviderError(
                f"Provider '{provider}' not configured. Available: {list(self.llm_clients.keys())}"
            )

        return self.llm_clients[provider]

    def get_quality_trends(self, window_size: int = 100) -> Dict[str, any]:
        """
        Get quality trend statistics.

        Args:
            window_size: Number of recent samples

        Returns:
            Quality trends
        """
        return self.quality_monitor.get_quality_trends(window_size)

    def get_performance_summary(
        self, time_window: Optional[timedelta] = None
    ) -> Dict[str, any]:
        """
        Get performance summary.

        Args:
            time_window: Optional time window

        Returns:
            Performance statistics
        """
        return self.performance_monitor.get_performance_summary(time_window)

    def get_circuit_breaker_status(self) -> Dict[str, any]:
        """
        Get circuit breaker status.

        Returns:
            Circuit breaker state
        """
        return self.circuit_breaker.get_state()

    def get_rate_limiter_status(self, user_id: Optional[str] = None) -> Dict[str, any]:
        """
        Get rate limiter status.

        Args:
            user_id: Optional user ID for user-specific stats

        Returns:
            Rate limiter status
        """
        status = {"global": self.rate_limiter.get_global_status()}

        if user_id:
            status["user_quota"] = self.rate_limiter.get_user_quota_status(user_id)

        return status
