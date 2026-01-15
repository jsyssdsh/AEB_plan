"""
Custom exception hierarchy for LLM Guardian.

All exceptions inherit from LLMGuardianError for easy catching.
"""

from typing import Any, Dict, Optional


class LLMGuardianError(Exception):
    """Base exception for all LLM Guardian errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


# Validation Errors


class ValidationError(LLMGuardianError):
    """Raised when input or output validation fails."""

    pass


class PromptInjectionError(ValidationError):
    """Raised when prompt injection attempt is detected."""

    pass


class ContentPolicyViolationError(ValidationError):
    """Raised when content violates safety policies."""

    pass


# Rate Limiting and Quota Errors


class RateLimitExceededError(LLMGuardianError):
    """Raised when rate limit is exceeded."""

    pass


class QuotaExceededError(LLMGuardianError):
    """Raised when quota (cost or token) is exceeded."""

    pass


class SessionBudgetExceededError(QuotaExceededError):
    """Raised when session budget is exceeded."""

    pass


class BudgetExceededError(QuotaExceededError):
    """Raised when per-request budget is exceeded."""

    pass


# Circuit Breaker Errors


class CircuitBreakerOpenError(LLMGuardianError):
    """Raised when circuit breaker is in OPEN state."""

    pass


class CircuitBreakerError(LLMGuardianError):
    """Base exception for circuit breaker errors."""

    pass


# Retry Errors


class RetryExhaustedError(LLMGuardianError):
    """Raised when all retry attempts are exhausted."""

    pass


class NonRetryableError(LLMGuardianError):
    """Raised for errors that should not be retried."""

    pass


# Monitoring Errors


class MonitoringError(LLMGuardianError):
    """Base exception for monitoring errors."""

    pass


class QualityCheckFailedError(MonitoringError):
    """Raised when quality check fails."""

    pass


class HallucinationDetectedError(QualityCheckFailedError):
    """Raised when hallucination is detected."""

    pass


class OffTaskResponseError(QualityCheckFailedError):
    """Raised when response is off-task."""

    pass


# LLM Provider Errors


class LLMProviderError(LLMGuardianError):
    """Base exception for LLM provider errors."""

    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when LLM provider request times out."""

    pass


class LLMProviderRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is hit."""

    pass


class LLMProviderAPIError(LLMProviderError):
    """Raised when LLM provider API returns an error."""

    pass


# State Management Errors


class StateManagementError(LLMGuardianError):
    """Base exception for state management errors."""

    pass


class CheckpointNotFoundError(StateManagementError):
    """Raised when checkpoint cannot be found."""

    pass


class CheckpointLoadError(StateManagementError):
    """Raised when checkpoint cannot be loaded."""

    pass


class CheckpointSaveError(StateManagementError):
    """Raised when checkpoint cannot be saved."""

    pass


# Configuration Errors


class ConfigurationError(LLMGuardianError):
    """Raised when configuration is invalid."""

    pass


class MissingAPIKeyError(ConfigurationError):
    """Raised when required API key is missing."""

    pass


# Integration Errors


class IntegrationError(LLMGuardianError):
    """Base exception for integration errors."""

    pass


class UnsupportedProviderError(IntegrationError):
    """Raised when LLM provider is not supported."""

    pass


class ModelNotAvailableError(IntegrationError):
    """Raised when requested model is not available."""

    pass
