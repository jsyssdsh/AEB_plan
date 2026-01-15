"""
Configuration management for LLM Guardian.

Uses Pydantic Settings to load configuration from environment variables
and .env files with type safety and validation.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitoringConfig(BaseSettings):
    """Configuration for monitoring components."""

    model_config = SettingsConfigDict(
        env_prefix="MONITORING__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    quality_alert_threshold: float = Field(
        default=0.6,
        description="Quality score threshold for alerts",
        ge=0.0,
        le=1.0,
    )
    performance_alert_threshold_ms: float = Field(
        default=5000.0,
        description="Latency threshold in ms for performance alerts",
        ge=0.0,
    )
    enable_anomaly_detection: bool = Field(
        default=True,
        description="Enable anomaly detection",
    )
    metrics_retention_days: int = Field(
        default=30,
        description="Number of days to retain metrics",
        ge=1,
    )


class SafetyConfig(BaseSettings):
    """Configuration for safety mechanisms."""

    model_config = SettingsConfigDict(
        env_prefix="SAFETY__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    circuit_breaker_threshold: int = Field(
        default=5,
        description="Number of failures before circuit opens",
        ge=1,
    )
    circuit_recovery_seconds: int = Field(
        default=60,
        description="Seconds before attempting recovery",
        ge=1,
    )
    max_prompt_length: int = Field(
        default=100000,
        description="Maximum prompt length in characters",
        ge=1,
    )
    enable_content_filtering: bool = Field(
        default=True,
        description="Enable content safety filtering",
    )


class RateLimitConfig(BaseSettings):
    """Configuration for rate limiting."""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMITING__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    global_max_requests_per_minute: int = Field(
        default=1000,
        description="Global rate limit (requests per minute)",
        ge=1,
    )
    user_max_requests_per_minute: int = Field(
        default=60,
        description="Per-user rate limit (requests per minute)",
        ge=1,
    )
    user_daily_quota_usd: Optional[float] = Field(
        default=100.0,
        description="Per-user daily quota in USD",
        ge=0.0,
    )
    session_budget_usd: Optional[float] = Field(
        default=10.0,
        description="Per-session budget in USD",
        ge=0.0,
    )


class RetryConfig(BaseSettings):
    """Configuration for retry strategy."""

    model_config = SettingsConfigDict(
        env_prefix="RETRY_STRATEGY__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts",
        ge=1,
        le=10,
    )
    initial_delay_seconds: float = Field(
        default=1.0,
        description="Initial delay before first retry",
        ge=0.1,
    )
    max_delay_seconds: float = Field(
        default=60.0,
        description="Maximum delay between retries",
        ge=1.0,
    )
    exponential_base: float = Field(
        default=2.0,
        description="Exponential backoff base",
        ge=1.0,
    )
    enable_jitter: bool = Field(
        default=True,
        description="Enable jitter to prevent thundering herd",
    )


class GuardianConfig(BaseSettings):
    """Main configuration for LLM Guardian."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested configurations
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    retry_strategy: RetryConfig = Field(default_factory=RetryConfig)

    # LLM provider credentials
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key",
    )

    # Storage paths
    state_storage_path: Path = Field(
        default=Path("/tmp/llm_guardian/state"),
        description="Path for state checkpoints",
    )
    audit_log_path: Path = Field(
        default=Path("/tmp/llm_guardian/audit"),
        description="Path for audit logs",
    )

    # Fallback provider configuration
    fallback_provider: Optional[str] = Field(
        default="openai",
        description="Fallback provider if primary fails",
    )
    fallback_model: Optional[str] = Field(
        default="gpt-3.5-turbo",
        description="Fallback model to use",
    )

    # Feature flags
    enable_monitoring: bool = Field(
        default=True,
        description="Enable monitoring features",
    )
    enable_safety_checks: bool = Field(
        default=True,
        description="Enable safety checks",
    )
    enable_recovery: bool = Field(
        default=True,
        description="Enable recovery mechanisms",
    )

    def validate_required_keys(self) -> None:
        """
        Validate that at least one API key is configured.

        Raises:
            ConfigurationError: If no API keys are configured
        """
        from llm_guardian.core.exceptions import MissingAPIKeyError

        if not self.anthropic_api_key and not self.openai_api_key:
            raise MissingAPIKeyError(
                "At least one LLM provider API key must be configured "
                "(ANTHROPIC_API_KEY or OPENAI_API_KEY)"
            )

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.state_storage_path.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.mkdir(parents=True, exist_ok=True)

    def model_post_init(self, __context: any) -> None:
        """Post-initialization hook to validate and setup."""
        # Create directories
        self.ensure_directories()


# Convenience function to load configuration
def load_config(env_file: Optional[str] = None) -> GuardianConfig:
    """
    Load Guardian configuration from environment.

    Args:
        env_file: Optional path to .env file

    Returns:
        GuardianConfig instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    if env_file:
        config = GuardianConfig(_env_file=env_file)  # type: ignore
    else:
        config = GuardianConfig()

    return config
