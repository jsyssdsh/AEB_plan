"""
Core domain models for LLM Guardian.

Implements Principle 3: Fundamental design quality through Pydantic models
with explicit contracts and validation at boundaries.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ResponseQuality(str, Enum):
    """Quality levels for LLM responses."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNSAFE = "unsafe"


class RequestContext(BaseModel):
    """
    Complete context for an LLM request with all assumptions explicit.

    This model enforces contracts at the boundary and makes all assumptions
    visible in the code (Principle 3).
    """

    request_id: str = Field(..., description="Unique request identifier", min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")

    # User context
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

    # Input validation
    prompt: str = Field(..., description="Input prompt", min_length=1, max_length=100000)
    max_tokens: int = Field(default=1000, description="Maximum tokens to generate", ge=1, le=32000)
    temperature: float = Field(default=0.7, description="Sampling temperature", ge=0.0, le=2.0)

    # Safety constraints
    allowed_topics: Optional[List[str]] = Field(
        None, description="Allowlist of permitted topics"
    )
    forbidden_patterns: Optional[List[str]] = Field(
        None, description="Regex patterns that are forbidden in prompt"
    )
    max_cost_usd: Optional[float] = Field(
        None, description="Maximum cost allowed for this request", ge=0.0
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        """Ensure prompt is not just whitespace."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "request_id": "req-12345",
                "user_id": "user-123",
                "prompt": "Explain quantum computing",
                "max_tokens": 500,
                "temperature": 0.7,
                "max_cost_usd": 0.10,
            }
        }


class LLMResponse(BaseModel):
    """
    LLM response with comprehensive quality and performance metrics.

    Contains all monitoring data needed for quality assessment and
    performance tracking (Principles 1 and 3).
    """

    request_id: str = Field(..., description="Matching request identifier")
    response_text: str = Field(..., description="Generated response text")

    # Performance metrics
    latency_ms: float = Field(..., description="Response latency in milliseconds", ge=0.0)
    tokens_used: int = Field(..., description="Total tokens used", ge=0)
    cost_usd: float = Field(..., description="Estimated cost in USD", ge=0.0)

    # Quality assessment (populated by monitoring)
    quality_score: float = Field(
        default=0.0, description="Overall quality score", ge=0.0, le=1.0
    )
    quality_level: ResponseQuality = Field(
        default=ResponseQuality.ACCEPTABLE, description="Quality level"
    )

    # Safety flags (populated by monitoring)
    contains_harmful_content: bool = Field(
        default=False, description="Whether response contains harmful content"
    )
    is_hallucination: bool = Field(
        default=False, description="Whether response is likely a hallucination"
    )
    is_off_task: bool = Field(
        default=False, description="Whether response is off-task or irrelevant"
    )

    # Provider metadata
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model identifier")
    raw_response: Dict[str, Any] = Field(..., description="Raw provider response")

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "request_id": "req-12345",
                "response_text": "Quantum computing uses quantum mechanics...",
                "latency_ms": 1250.5,
                "tokens_used": 150,
                "cost_usd": 0.0045,
                "quality_score": 0.85,
                "quality_level": "good",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "raw_response": {},
            }
        }


class MonitoringAlert(BaseModel):
    """Alert raised by monitoring system when issues are detected."""

    alert_id: str = Field(..., description="Unique alert identifier")
    severity: str = Field(
        ...,
        description="Alert severity level",
        pattern="^(low|medium|high|critical)$",
    )
    category: str = Field(
        ...,
        description="Alert category",
        pattern="^(quality|performance|safety|anomaly|budget)$",
    )
    message: str = Field(..., description="Human-readable alert message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Alert timestamp")
    resolved: bool = Field(default=False, description="Whether alert has been resolved")

    # Optional reference to related request
    request_id: Optional[str] = Field(None, description="Related request ID if applicable")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "alert_id": "alert-789",
                "severity": "high",
                "category": "quality",
                "message": "Quality score below threshold",
                "details": {"quality_score": 0.45, "threshold": 0.6},
                "request_id": "req-12345",
            }
        }


class QualityAssessment(BaseModel):
    """Detailed quality assessment for an LLM response."""

    request_id: str = Field(..., description="Request identifier")

    # Quality scores
    hallucination_probability: float = Field(
        default=0.0,
        description="Probability that response is a hallucination",
        ge=0.0,
        le=1.0,
    )
    safety_violations: List[str] = Field(
        default_factory=list, description="List of safety violations detected"
    )
    coherence_score: float = Field(
        default=1.0, description="Response coherence score", ge=0.0, le=1.0
    )
    relevance_score: float = Field(
        default=1.0, description="Response relevance to prompt", ge=0.0, le=1.0
    )

    # Recommendations
    pass_validation: bool = Field(
        default=True, description="Whether response passes validation"
    )
    recommended_action: str = Field(
        default="accept",
        description="Recommended action",
        pattern="^(accept|reject|review|fallback)$",
    )
    warnings: List[str] = Field(default_factory=list, description="Quality warnings")

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Assessment timestamp"
    )


class PerformanceMetrics(BaseModel):
    """Performance metrics for an LLM request."""

    request_id: str = Field(..., description="Request identifier")
    latency_ms: float = Field(..., description="Latency in milliseconds", ge=0.0)

    # Token metrics
    tokens_prompt: int = Field(..., description="Prompt tokens", ge=0)
    tokens_completion: int = Field(..., description="Completion tokens", ge=0)
    tokens_total: int = Field(..., description="Total tokens", ge=0)

    # Cost metrics
    cost_usd: float = Field(..., description="Request cost in USD", ge=0.0)

    # Provider info
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model identifier")

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "request_id": "req-12345",
                "latency_ms": 1250.5,
                "tokens_prompt": 50,
                "tokens_completion": 100,
                "tokens_total": 150,
                "cost_usd": 0.0045,
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            }
        }


class StateSnapshot(BaseModel):
    """Snapshot of system state for recovery purposes."""

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    request_context: RequestContext = Field(..., description="Request context")
    response: Optional[LLMResponse] = Field(None, description="Response if available")
    checkpoint_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional checkpoint data"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Snapshot timestamp")

    class Config:
        """Pydantic model configuration."""

        # Allow arbitrary types for nested models
        arbitrary_types_allowed = True


class ValidationResult(BaseModel):
    """Result of input or output validation."""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    severity: str = Field(
        default="low",
        description="Severity if invalid",
        pattern="^(low|medium|high|critical)$",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "is_valid": False,
                "errors": ["Prompt exceeds maximum length"],
                "warnings": ["Unusual prompt structure detected"],
                "severity": "medium",
            }
        }
