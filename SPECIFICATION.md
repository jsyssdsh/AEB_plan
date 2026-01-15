# LLM Guardian - Technical Specification

**Version:** 0.1.0
**Date:** January 2026
**Status:** Initial Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Architecture](#architecture)
4. [Component Specifications](#component-specifications)
5. [Data Models](#data-models)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Performance Characteristics](#performance-characteristics)
10. [Security Considerations](#security-considerations)

---

## Overview

LLM Guardian is a comprehensive monitoring and safety system for LLM/Agent applications. It provides enterprise-grade protection through real-time monitoring, safety mechanisms, and intelligent recovery systems.

### Purpose

Provide a unified framework for:
- Detecting quality and safety issues in LLM outputs (early warning)
- Preventing cascading failures and enabling recovery (resilience)
- Enforcing contracts and validation at all boundaries (design quality)

### Target Applications

- LLM-powered chatbots and assistants
- Autonomous agent systems
- LLM API services
- AI-augmented applications
- Research platforms requiring safety guarantees

---

## Core Principles

The system implements three fundamental principles from AI safety research:

### Principle 1: Monitoring as Early Warning System

**Definition:** Identify gaps between actual measurements and assumptions before they cause problems.

**Implementation:**
- Real-time quality monitoring of LLM outputs
- Performance tracking with anomaly detection
- Continuous trend analysis
- Alerting system for threshold violations

**Key Insight:** Monitoring is not just for debugging—it's a critical early warning system that catches problems before they cascade.

### Principle 2: Recovery Mechanisms

**Definition:** Enable system restoration after failures through intelligent recovery strategies.

**Implementation:**
- Circuit breaker pattern to prevent cascading failures
- Exponential backoff retry with jitter
- State persistence for recovery
- Graceful degradation with fallback providers
- Comprehensive audit logging

**Key Insight:** Software redundancy and recovery are less effective than expected; focus on fundamental design quality while implementing practical recovery mechanisms.

### Principle 3: Fundamental Design Quality

**Definition:** Ensure correctness through validation at boundaries, clear contracts, and type safety.

**Implementation:**
- Pydantic models enforcing contracts at runtime
- Comprehensive input/output validation
- Explicit assumptions in code
- Type hints throughout codebase
- Schema validation at all boundaries

**Key Insight:** The most effective safety comes from correct design and explicit requirements, not just recovery mechanisms.

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              (User's LLM/Agent Application)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLMGuardian Orchestrator                    │
│         (Coordinates all monitoring and safety)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Safety     │ │  Monitoring  │ │   Recovery   │
│   Layer      │ │    Layer     │ │    Layer     │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
            ┌─────────────────────┐
            │  LLM Provider APIs  │
            │ (Anthropic, OpenAI) │
            └─────────────────────┘
```

### Layered Design

**Layer 1: Application Layer**
- User's LLM/Agent application code
- Integrates with Guardian via simple API

**Layer 2: Safety Wrapper Layer**
- Circuit breakers
- Rate limiting
- Input/output validation
- Content filtering

**Layer 3: Monitoring Layer**
- Quality checks (hallucination, safety, relevance)
- Performance tracking (latency, tokens, costs)
- Anomaly detection
- Alerting

**Layer 4: Recovery Layer**
- Retry logic with exponential backoff
- State management and checkpointing
- Audit logging
- Graceful degradation

**Layer 5: Integration Layer**
- Provider-agnostic LLM client interface
- Anthropic Claude client
- OpenAI GPT client
- Cost estimation

### Request Flow

```
1. Request arrives → Audit log
2. Input validation → Check for injection, length, patterns
3. Rate limiting → Check quotas and limits
4. Save checkpoint → State persistence
5. Execute with circuit breaker → Prevent cascading failures
   ├─ Retry on transient failures → Exponential backoff
   └─ Fallback provider if primary fails
6. Quality monitoring → Check for hallucinations, safety, relevance
7. Performance monitoring → Record latency, tokens, costs
8. Output validation → Verify quality thresholds
9. Audit log response → Complete audit trail
10. Return response → With full monitoring metadata
```

---

## Component Specifications

### 1. Quality Monitor

**File:** `llm_guardian/monitoring/quality_monitor.py`

**Purpose:** Implement Principle 1 (early warning) by detecting quality issues in LLM outputs.

**Components:**

#### HallucinationDetector
- **Input:** LLM response text
- **Output:** Probability score (0.0-1.0)
- **Method:** Pattern matching + heuristics
- **Patterns Detected:**
  - Uncertainty markers ("I don't actually have access to...")
  - Fabrication admissions ("I made up...")
  - Knowledge cutoff references
  - Confidence disclaimers
- **Threshold:** 0.7 (configurable)

#### ContentSafetyChecker
- **Input:** LLM response text
- **Output:** Safety assessment with violations list
- **Categories:**
  - Violence
  - Hate speech
  - Self-harm
  - Sexual content
  - Illegal activity
- **Method:** Multi-pattern regex matching per category
- **Threshold:** 0.5 per category

#### OffTaskDetector
- **Input:** LLM response + original prompt
- **Output:** Boolean (is off-task)
- **Method:** Keyword overlap analysis
- **Threshold:** 0.6 similarity

#### QualityMonitor (Main)
- **Coordinates:** All quality checks
- **Outputs:** QualityAssessment with:
  - Overall quality score (0.0-1.0)
  - Quality level (EXCELLENT/GOOD/ACCEPTABLE/POOR/UNSAFE)
  - Hallucination probability
  - Safety violations list
  - Warnings list
  - Pass/fail validation status
  - Recommended action (accept/reject/review/fallback)
- **Alerting:** Raises alerts when quality < threshold
- **Trend Tracking:** Maintains rolling window of quality scores

### 2. Performance Monitor

**File:** `llm_guardian/monitoring/performance_monitor.py`

**Purpose:** Track operational metrics and enforce budgets.

**Metrics Tracked:**
- Latency (ms) with percentiles (p50, p95, p99)
- Token usage (prompt, completion, total)
- Costs (USD)
- Provider/model metadata

**Budget Enforcement:**
- Per-request budget limits
- Per-session budget tracking
- Per-user daily quotas with automatic reset

**Anomaly Detection:**
- Alert when latency > 2x p95
- Alert when latency > configured threshold
- Track performance trends over time

**Cost Tracking:**
- Session-level cost accumulation
- User-level daily cost accumulation
- Automatic daily reset per user

### 3. Circuit Breaker

**File:** `llm_guardian/safety/circuit_breaker.py`

**Purpose:** Implement Principle 2 (recovery) by preventing cascading failures.

**States:**
- **CLOSED:** Normal operation, requests pass through
- **OPEN:** Blocking all requests, system recovering
- **HALF_OPEN:** Testing recovery, allowing limited requests

**State Transitions:**
- CLOSED → OPEN: After `failure_threshold` consecutive failures (default: 5)
- OPEN → HALF_OPEN: After `recovery_timeout` (default: 60s)
- HALF_OPEN → CLOSED: After `success_threshold` successes (default: 2)
- HALF_OPEN → OPEN: On any failure

**Configuration:**
```python
CircuitBreaker(
    failure_threshold=5,      # Failures before opening
    recovery_timeout=60s,     # Wait before retry
    success_threshold=2,      # Successes to close
    expected_exception=Exception  # What to catch
)
```

**Statistics Tracked:**
- Total calls, failures, successes
- Failure rate
- Time in each state
- State change history

### 4. Rate Limiter

**File:** `llm_guardian/safety/rate_limiter.py`

**Purpose:** Prevent resource exhaustion through multi-level rate limiting.

**Algorithms:**

#### TokenBucket
- Smooth rate limiting with token refill
- Capacity: max burst size
- Refill rate: tokens per second
- Used for: Global and per-user limits

#### SlidingWindow
- Precise windowed rate limiting
- Tracks exact request timestamps
- Removes expired requests from window

**Limit Levels:**
1. **Global Rate Limit**
   - Requests per minute across all users
   - Default: 1000 RPM
   - Token bucket algorithm

2. **Per-User Rate Limit**
   - Requests per minute per user
   - Default: 60 RPM
   - Separate token bucket per user

3. **Cost-Based Quotas**
   - Per-user daily quota (USD)
   - Default: $100/day
   - Automatic reset at midnight UTC

4. **Session Budgets**
   - Per-session cost limit (USD)
   - Default: $10/session
   - No automatic reset

### 5. Input Validator

**File:** `llm_guardian/safety/validators.py`

**Purpose:** Implement Principle 3 (validation at boundaries) for inputs.

**Validations:**

1. **Schema Validation**
   - Via Pydantic models
   - Automatic at object construction
   - Type checking, range validation

2. **Prompt Injection Detection**
   - Pattern matching for injection attempts
   - Patterns detected:
     - "ignore previous instructions"
     - "disregard all prior rules"
     - System prompt override attempts
     - Chat format markers
   - Action: Reject request with PromptInjectionError

3. **Length Validation**
   - Max prompt length: 100,000 chars (configurable)
   - Prevents resource exhaustion

4. **Forbidden Pattern Checking**
   - User-defined regex patterns
   - Custom content restrictions
   - Per-request configuration

5. **Topic Allowlisting**
   - Optional keyword-based topic checking
   - Ensures prompts stay within allowed domains

### 6. Output Validator

**File:** `llm_guardian/safety/validators.py`

**Purpose:** Validate LLM outputs before returning to user.

**Validations:**

1. **Safety Requirements**
   - Must not contain harmful content (critical)
   - Checked via ContentSafetyChecker

2. **Quality Thresholds**
   - Quality score must be ≥ 0.5
   - Prevents low-quality responses

3. **Hallucination Checks**
   - Must not be flagged as hallucination
   - Based on HallucinationDetector

4. **Completeness**
   - Response must not be empty
   - Response length > 10 chars recommended

5. **On-Task Verification**
   - Warning if response is off-task
   - Not blocking, but logged

### 7. Retry Manager

**File:** `llm_guardian/recovery/retry_manager.py`

**Purpose:** Implement Principle 2 (recovery) through intelligent retry logic.

**Strategy:**

```python
RetryStrategy(
    max_attempts=3,          # Maximum retries
    initial_delay=1.0,       # Initial delay (seconds)
    max_delay=60.0,          # Max delay cap (seconds)
    exponential_base=2.0,    # Backoff multiplier
    jitter=True              # Add randomization
)
```

**Exponential Backoff:**
```
Attempt 1: initial_delay * (base^0) = 1.0s
Attempt 2: initial_delay * (base^1) = 2.0s
Attempt 3: initial_delay * (base^2) = 4.0s
...
Capped at max_delay
```

**Jitter:**
```
actual_delay = calculated_delay * (0.5 + random() * 0.5)
```
- Prevents thundering herd problem
- Distributes retry attempts over time

**Retryable Errors:**
- ConnectionError
- TimeoutError
- LLMProviderTimeoutError
- LLMProviderRateLimitError

**Non-Retryable Errors:**
- ValidationError
- AuthenticationError
- Any other exceptions (fail fast)

### 8. State Manager

**File:** `llm_guardian/recovery/state_manager.py`

**Purpose:** Enable recovery through state persistence.

**Checkpoint Structure:**
```json
{
  "snapshot_id": "request-id",
  "request_context": { /* RequestContext */ },
  "checkpoint_data": {
    "stage": "pre_execution|completed",
    "response_id": "optional"
  },
  "timestamp": "ISO 8601"
}
```

**Storage:**
- File-based: `{state_storage_path}/{request_id}.json`
- Async I/O using aiofiles
- One file per request

**Operations:**
- `save_checkpoint()`: Persist state
- `load_checkpoint()`: Recover state
- `delete_checkpoint()`: Cleanup

**Use Cases:**
- Recovery after system crash
- Debugging failed requests
- Request replay for testing

### 9. Audit Logger

**File:** `llm_guardian/recovery/audit_logger.py`

**Purpose:** Comprehensive audit trail for compliance and debugging.

**Log Format:** JSON Lines (one JSON object per line)

**Event Types:**

1. **Request Events**
```json
{
  "timestamp": "2026-01-14T12:00:00Z",
  "event_type": "request",
  "request_id": "req-123",
  "user_id": "user-456",
  "session_id": "session-789",
  "prompt_length": 100,
  "prompt_preview": "First 100 chars...",
  "max_tokens": 500,
  "temperature": 0.7,
  "metadata": {}
}
```

2. **Response Events**
```json
{
  "timestamp": "2026-01-14T12:00:01Z",
  "event_type": "response",
  "request_id": "req-123",
  "response_length": 250,
  "response_preview": "First 100 chars...",
  "latency_ms": 1250.5,
  "tokens_used": 150,
  "cost_usd": 0.0045,
  "quality_score": 0.85,
  "quality_level": "good",
  "contains_harmful_content": false,
  "is_hallucination": false,
  "is_off_task": false,
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022"
}
```

3. **Error Events**
```json
{
  "timestamp": "2026-01-14T12:00:01Z",
  "event_type": "error",
  "request_id": "req-123",
  "error_type": "ValidationError",
  "error_message": "Input validation failed",
  "context": {}
}
```

4. **Alert Events**
```json
{
  "timestamp": "2026-01-14T12:00:01Z",
  "event_type": "alert",
  "alert_id": "alert-456",
  "severity": "high",
  "category": "quality",
  "message": "Quality score below threshold",
  "details": {},
  "request_id": "req-123"
}
```

**Log Rotation:**
- One file per day: `audit_{YYYYMMDD}.jsonl`
- Automatic rotation at midnight UTC
- Manual retention policy (not automated)

### 10. LLM Provider Clients

**Files:**
- `llm_guardian/integrations/base.py`
- `llm_guardian/integrations/anthropic_client.py`
- `llm_guardian/integrations/openai_client.py`

**Base Interface:**
```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        context: RequestContext,
        model: str
    ) -> LLMResponse:
        """Generate LLM response"""

    @abstractmethod
    def estimate_cost(
        self,
        tokens_prompt: int,
        tokens_completion: int,
        model: str
    ) -> float:
        """Estimate cost in USD"""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
```

**AnthropicClient:**
- Uses `anthropic` Python SDK
- Supported models:
  - claude-3-5-sonnet-20241022
  - claude-3-5-haiku-20241022
  - claude-3-opus-20240229
- Pricing (per million tokens, Jan 2025):
  - Sonnet 4.5: $3 input, $15 output
  - Haiku: $0.80 input, $4 output
  - Opus: $15 input, $75 output

**OpenAIClient:**
- Uses `openai` Python SDK
- Supported models:
  - gpt-4-turbo
  - gpt-4
  - gpt-3.5-turbo
- Pricing (per million tokens, Jan 2025):
  - GPT-4 Turbo: $10 input, $30 output
  - GPT-4: $30 input, $60 output
  - GPT-3.5 Turbo: $0.50 input, $1.50 output

### 11. Guardian Orchestrator

**File:** `llm_guardian/core/guardian.py`

**Purpose:** Main entry point coordinating all components.

**Initialization:**
```python
guardian = LLMGuardian(config)
```

**Main Method:**
```python
async def execute_request(
    context: RequestContext,
    provider: str = "anthropic",
    model: str = "claude-3-5-sonnet-20241022"
) -> LLMResponse
```

**Execution Flow:**
1. Audit log request
2. Input validation (if enabled)
3. Rate limit check
4. Save checkpoint
5. Execute with circuit breaker + retry
   - Call LLM provider
   - Retry on transient failures
   - Fallback to alternate provider if configured
6. Quality monitoring (if enabled)
7. Performance monitoring (if enabled)
8. Output validation (if enabled)
9. Audit log response
10. Update checkpoint
11. Return response

**Status Methods:**
```python
get_quality_trends(window_size: int) -> Dict
get_performance_summary(time_window: timedelta) -> Dict
get_circuit_breaker_status() -> Dict
get_rate_limiter_status(user_id: str) -> Dict
```

---

## Data Models

All models use Pydantic for validation (Principle 3).

### RequestContext

**Purpose:** Complete context for an LLM request with explicit assumptions.

**Fields:**
```python
request_id: str              # Unique identifier
timestamp: datetime          # Request timestamp
user_id: Optional[str]       # User identifier
session_id: Optional[str]    # Session identifier

# Input
prompt: str                  # Input prompt (1-100000 chars)
max_tokens: int              # Max generation tokens (1-32000)
temperature: float           # Sampling temperature (0.0-2.0)

# Safety constraints
allowed_topics: Optional[List[str]]       # Topic allowlist
forbidden_patterns: Optional[List[str]]   # Forbidden regex patterns
max_cost_usd: Optional[float]            # Budget limit (≥0)

# Metadata
metadata: Dict[str, Any]     # Additional metadata
```

**Validation:**
- Prompt cannot be empty/whitespace
- All numeric ranges enforced
- Type checking via Pydantic

### LLMResponse

**Purpose:** LLM response with comprehensive metrics.

**Fields:**
```python
request_id: str              # Matching request ID
response_text: str           # Generated text

# Performance
latency_ms: float            # Latency (≥0)
tokens_used: int             # Total tokens (≥0)
cost_usd: float              # Cost (≥0)

# Quality (populated by monitoring)
quality_score: float         # Overall quality (0.0-1.0)
quality_level: ResponseQuality  # EXCELLENT/GOOD/ACCEPTABLE/POOR/UNSAFE

# Safety flags
contains_harmful_content: bool   # Harmful content detected
is_hallucination: bool           # Hallucination detected
is_off_task: bool                # Off-task response

# Provider
provider: str                # Provider name
model: str                   # Model identifier
raw_response: Dict[str, Any] # Raw provider response

timestamp: datetime          # Response timestamp
```

### QualityAssessment

**Purpose:** Detailed quality assessment results.

**Fields:**
```python
request_id: str

# Scores
hallucination_probability: float   # 0.0-1.0
safety_violations: List[str]       # Categories violated
coherence_score: float             # 0.0-1.0
relevance_score: float             # 0.0-1.0

# Recommendations
pass_validation: bool
recommended_action: str  # accept/reject/review/fallback
warnings: List[str]

timestamp: datetime
```

### PerformanceMetrics

**Purpose:** Performance metrics for request.

**Fields:**
```python
request_id: str
latency_ms: float

# Tokens
tokens_prompt: int
tokens_completion: int
tokens_total: int

# Cost
cost_usd: float

# Provider
provider: str
model: str

timestamp: datetime
```

### MonitoringAlert

**Purpose:** Alert for monitoring issues.

**Fields:**
```python
alert_id: str
severity: str  # low/medium/high/critical
category: str  # quality/performance/safety/anomaly/budget
message: str
details: Dict[str, Any]
timestamp: datetime
resolved: bool
request_id: Optional[str]
```

### ValidationResult

**Purpose:** Input/output validation result.

**Fields:**
```python
is_valid: bool
errors: List[str]
warnings: List[str]
severity: str  # low/medium/high/critical
```

---

## API Reference

### LLMGuardian

Main orchestrator class.

#### Constructor

```python
LLMGuardian(config: GuardianConfig)
```

**Parameters:**
- `config`: Configuration object

**Raises:**
- `MissingAPIKeyError`: If no API keys configured

#### Methods

##### execute_request()

```python
async def execute_request(
    context: RequestContext,
    provider: str = "anthropic",
    model: str = "claude-3-5-sonnet-20241022"
) -> LLMResponse
```

Execute LLM request with full monitoring and safety.

**Parameters:**
- `context`: Request context with prompt and constraints
- `provider`: LLM provider ("anthropic" or "openai")
- `model`: Model identifier

**Returns:**
- `LLMResponse` with monitoring metadata

**Raises:**
- `ValidationError`: Validation failed
- `RateLimitExceededError`: Rate limit exceeded
- `QuotaExceededError`: Quota exceeded
- `CircuitBreakerOpenError`: Circuit breaker open
- `PromptInjectionError`: Prompt injection detected
- `LLMProviderError`: Provider error

##### get_quality_trends()

```python
def get_quality_trends(window_size: int = 100) -> Dict[str, float]
```

Get quality trend statistics.

**Returns:**
```python
{
    "mean_quality": 0.85,
    "std_quality": 0.10,
    "min_quality": 0.60,
    "max_quality": 0.95,
    "p50_quality": 0.85,
    "p95_quality": 0.92,
    "sample_count": 100
}
```

##### get_performance_summary()

```python
def get_performance_summary(
    time_window: Optional[timedelta] = None
) -> Dict[str, any]
```

Get performance summary.

**Returns:**
```python
{
    "request_count": 1000,
    "latency_mean": 1250.5,
    "latency_p50": 1100.0,
    "latency_p95": 2000.0,
    "latency_p99": 3000.0,
    "latency_min": 500.0,
    "latency_max": 5000.0,
    "total_cost_usd": 5.50,
    "avg_cost_usd": 0.0055,
    "total_tokens": 150000,
    "avg_tokens": 150
}
```

##### get_circuit_breaker_status()

```python
def get_circuit_breaker_status() -> Dict[str, any]
```

Get circuit breaker state.

**Returns:**
```python
{
    "state": "closed",
    "failure_count": 0,
    "success_count": 100,
    "last_failure_time": None,
    "last_state_change": "2026-01-14T12:00:00Z",
    "time_until_retry": 0.0,
    "total_calls": 100,
    "total_failures": 0,
    "total_successes": 100,
    "failure_rate": 0.0
}
```

##### get_rate_limiter_status()

```python
def get_rate_limiter_status(user_id: Optional[str] = None) -> Dict[str, any]
```

Get rate limiter status.

**Returns:**
```python
{
    "global": {
        "available_tokens": 950.5,
        "capacity": 1000,
        "refill_rate_per_second": 16.67
    },
    "user_quota": {  # If user_id provided
        "user_id": "user-123",
        "current_usage_usd": 2.50,
        "daily_limit_usd": 100.0,
        "remaining_usd": 97.50,
        "usage_percentage": 2.5,
        "last_reset": "2026-01-14T00:00:00Z"
    }
}
```

---

## Configuration

### GuardianConfig

Main configuration class using Pydantic Settings.

**Environment Variables:**

```bash
# LLM Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Monitoring
MONITORING__QUALITY_ALERT_THRESHOLD=0.6
MONITORING__PERFORMANCE_ALERT_THRESHOLD_MS=5000
MONITORING__ENABLE_ANOMALY_DETECTION=true
MONITORING__METRICS_RETENTION_DAYS=30

# Safety
SAFETY__CIRCUIT_BREAKER_THRESHOLD=5
SAFETY__CIRCUIT_RECOVERY_SECONDS=60
SAFETY__MAX_PROMPT_LENGTH=100000
SAFETY__ENABLE_CONTENT_FILTERING=true

# Rate Limiting
RATE_LIMITING__GLOBAL_MAX_REQUESTS_PER_MINUTE=1000
RATE_LIMITING__USER_MAX_REQUESTS_PER_MINUTE=60
RATE_LIMITING__USER_DAILY_QUOTA_USD=100.0
RATE_LIMITING__SESSION_BUDGET_USD=10.0

# Retry
RETRY_STRATEGY__MAX_ATTEMPTS=3
RETRY_STRATEGY__INITIAL_DELAY_SECONDS=1.0
RETRY_STRATEGY__MAX_DELAY_SECONDS=60.0
RETRY_STRATEGY__EXPONENTIAL_BASE=2.0
RETRY_STRATEGY__ENABLE_JITTER=true

# Storage
STATE_STORAGE_PATH=/tmp/llm_guardian/state
AUDIT_LOG_PATH=/tmp/llm_guardian/audit

# Fallback
FALLBACK_PROVIDER=openai
FALLBACK_MODEL=gpt-3.5-turbo
```

**Loading Configuration:**

```python
from llm_guardian import GuardianConfig

# Load from environment and .env file
config = GuardianConfig()

# Load from specific .env file
config = GuardianConfig(_env_file="/path/to/.env")
```

**Nested Configuration:**

```python
config.monitoring.quality_alert_threshold      # 0.6
config.safety.circuit_breaker_threshold        # 5
config.rate_limiting.user_max_requests_per_minute  # 60
config.retry_strategy.max_attempts             # 3
```

---

## Deployment

### Requirements

**Python Version:** 3.10+

**Dependencies:**
```
pydantic>=2.5.0
pydantic-settings>=2.1.0
aiofiles>=23.2.1
anthropic>=0.18.0
openai>=1.12.0
numpy>=1.26.0
structlog>=24.1.0
python-dotenv>=1.0.0
```

**Optional:**
```
pandas>=2.1.0           # Advanced analytics
scikit-learn>=1.4.0     # ML-based anomaly detection
```

### Installation

```bash
# Production
pip install llm-guardian

# Development
pip install -e ".[dev]"

# All features
pip install -e ".[all]"
```

### Configuration Setup

1. **Create .env file:**
```bash
cp .env.example .env
```

2. **Add API keys:**
```bash
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

3. **Customize settings** (optional):
```bash
MONITORING__QUALITY_ALERT_THRESHOLD=0.7
RATE_LIMITING__USER_MAX_REQUESTS_PER_MINUTE=100
```

### Basic Usage

```python
import asyncio
from llm_guardian import LLMGuardian, RequestContext, GuardianConfig

async def main():
    # Initialize
    config = GuardianConfig()
    guardian = LLMGuardian(config)

    # Create request
    context = RequestContext(
        request_id="req-001",
        user_id="user-123",
        prompt="Explain quantum computing",
        max_tokens=500,
        temperature=0.7,
        max_cost_usd=0.10
    )

    # Execute with monitoring
    response = await guardian.execute_request(
        context,
        provider="anthropic",
        model="claude-3-5-sonnet-20241022"
    )

    # Use response
    print(f"Response: {response.response_text}")
    print(f"Quality: {response.quality_score}")
    print(f"Cost: ${response.cost_usd:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Docker Deployment (Future)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY llm_guardian/ ./llm_guardian/
COPY .env .

CMD ["python", "your_app.py"]
```

---

## Performance Characteristics

### Latency Overhead

**Monitoring Overhead:** < 10% latency increase

**Breakdown:**
- Input validation: ~1-5ms
- Rate limiting check: ~1ms (token bucket)
- Quality monitoring: ~10-50ms (pattern matching)
- Performance monitoring: ~1ms (metric recording)
- Output validation: ~5-10ms
- Audit logging: ~2-5ms (async writes)

**Total overhead:** ~20-75ms typical (< 100ms p95)

**For 1000ms LLM request:**
- Without Guardian: 1000ms
- With Guardian: ~1050ms (5% overhead)

### Throughput

**Rate Limiting Capacity:**
- Global: 1000 requests/minute = ~16.7 req/s
- Per-user: 60 requests/minute = 1 req/s

**Bottlenecks:**
- LLM provider API (primary)
- Disk I/O for audit logging (async, minimal impact)
- Memory for historical metrics (10,000 samples cached)

### Memory Usage

**Per Request:**
- RequestContext: ~2KB
- LLMResponse: ~5-50KB (depends on response length)
- Monitoring data: ~1KB
- Total: ~10-55KB per request

**Historical Data:**
- Quality history: 1,000 samples × 8 bytes = 8KB
- Performance history: 10,000 samples × ~100 bytes = ~1MB
- Circuit breaker: ~1KB
- Rate limiter: ~1KB per user
- Total: ~2-5MB for typical usage

### Scalability

**Horizontal Scaling:**
- Stateless design (except in-memory metrics)
- Can run multiple instances with shared storage
- Audit logs are per-instance (merge for analysis)

**Limitations:**
- In-memory metrics not shared across instances
- Circuit breaker state per instance
- Rate limiting needs distributed coordination for true global limits

**Recommended:**
- Use external rate limiting (e.g., Redis) for distributed systems
- Use external metrics storage (e.g., Prometheus) for monitoring
- Centralized audit log aggregation (e.g., ELK stack)

---

## Security Considerations

### Input Security

**Prompt Injection Protection:**
- Pattern-based detection
- Immediate rejection with error
- Logged to audit trail

**Limitations:**
- Pattern matching can have false positives/negatives
- Advanced injection techniques may bypass detection
- Recommend: Additional app-level validation

**Best Practices:**
- Validate user input before passing to Guardian
- Use topic allowlists when possible
- Define forbidden patterns for sensitive domains
- Review audit logs for injection attempts

### Output Security

**Content Filtering:**
- Multi-category safety checking
- Critical severity blocks response
- Logged to audit trail

**Limitations:**
- Pattern-based detection not perfect
- Context-dependent content may be misclassified
- Recommend: Human review for high-risk applications

**Best Practices:**
- Set appropriate quality thresholds
- Enable content filtering in production
- Review flagged responses
- Train team on quality assessment

### API Key Security

**Storage:**
- Environment variables (recommended)
- .env files (development only, add to .gitignore)
- Secret management services (production)

**Best Practices:**
- Never commit API keys to version control
- Rotate keys regularly
- Use separate keys for dev/staging/prod
- Monitor API usage for anomalies

### Audit Trail Security

**Log Contents:**
- Prompt previews (first 100 chars)
- Response previews (first 100 chars)
- Full metadata (tokens, costs, quality)
- Error details

**Sensitive Data:**
- Full prompts/responses NOT logged by default
- User IDs logged (consider anonymization)
- Timestamps logged (consider privacy implications)

**Best Practices:**
- Secure audit log storage (proper permissions)
- Encrypt audit logs at rest
- Implement log retention policy
- Consider GDPR/privacy requirements

### Rate Limiting Security

**DoS Prevention:**
- Global rate limits prevent service exhaustion
- Per-user limits prevent individual abuse
- Cost quotas prevent budget overruns

**Bypass Risks:**
- User ID manipulation (if not authenticated)
- Multiple API keys (organizational control)
- Distributed attacks (need external rate limiting)

**Best Practices:**
- Implement authentication before Guardian
- Use authenticated user IDs
- Monitor for unusual patterns
- Implement IP-based rate limiting (external)

---

## Appendix

### Error Handling

**Exception Hierarchy:**

```
LLMGuardianError (base)
├── ValidationError
│   ├── PromptInjectionError
│   └── ContentPolicyViolationError
├── RateLimitExceededError
│   ├── QuotaExceededError
│   ├── SessionBudgetExceededError
│   └── BudgetExceededError
├── CircuitBreakerError
│   └── CircuitBreakerOpenError
├── RetryExhaustedError
├── MonitoringError
│   ├── QualityCheckFailedError
│   ├── HallucinationDetectedError
│   └── OffTaskResponseError
├── LLMProviderError
│   ├── LLMProviderTimeoutError
│   ├── LLMProviderRateLimitError
│   └── LLMProviderAPIError
├── StateManagementError
│   ├── CheckpointNotFoundError
│   ├── CheckpointLoadError
│   └── CheckpointSaveError
├── ConfigurationError
│   └── MissingAPIKeyError
└── IntegrationError
    ├── UnsupportedProviderError
    └── ModelNotAvailableError
```

### Testing Strategy

**Unit Tests:**
- Test each component in isolation
- Mock external dependencies
- Focus on edge cases

**Integration Tests:**
- Test component interactions
- Use test doubles for LLM APIs
- Test failure scenarios

**Contract Tests:**
- Verify Pydantic model contracts
- Test boundary validations
- Ensure type safety

**Performance Tests:**
- Load testing (concurrent requests)
- Latency measurement
- Resource usage profiling

**Chaos Tests:**
- Inject failures
- Test circuit breaker
- Verify graceful degradation

### Monitoring Recommendations

**Metrics to Track:**
- Request rate (req/s)
- Latency percentiles (p50, p95, p99)
- Error rate (%)
- Quality score distribution
- Cost per request
- Circuit breaker state changes
- Rate limit violations

**Alerting Rules:**
- Error rate > 5% (critical)
- Latency p95 > 5s (warning)
- Quality score < 0.5 (warning)
- Circuit breaker opens (critical)
- Cost spike > 2x average (warning)

**Dashboards:**
- Real-time request throughput
- Quality trends over time
- Cost breakdown by user/model
- Error distribution by type
- Circuit breaker status

### Future Enhancements

**Planned Features:**
- Distributed rate limiting (Redis)
- Advanced anomaly detection (ML-based)
- Real-time dashboard
- Multi-provider circuit breakers
- Embedding-based similarity for off-task detection
- Custom quality check plugins
- Prometheus metrics export
- OpenTelemetry integration

**Possible Integrations:**
- LangChain/LlamaIndex compatibility
- Guardrails AI integration
- LangSmith tracing
- Weights & Biases logging

---

## Glossary

**Circuit Breaker:** Pattern that prevents cascading failures by temporarily blocking requests to a failing service.

**Exponential Backoff:** Retry strategy where delay increases exponentially with each attempt.

**Hallucination:** When an LLM generates plausible-sounding but factually incorrect or fabricated information.

**Jitter:** Random variation added to retry delays to prevent synchronized retries (thundering herd).

**Prompt Injection:** Attack technique where malicious input attempts to override system instructions.

**Quality Score:** Numeric assessment (0.0-1.0) of LLM response quality based on multiple factors.

**Rate Limiting:** Technique to control request frequency to prevent resource exhaustion.

**Token Bucket:** Algorithm for smooth rate limiting where tokens are consumed per request and refilled over time.

---

## References

### Core Principles Source
- Based on AI system safety principles emphasizing:
  1. Monitoring as early warning (not just debugging)
  2. Recovery mechanisms (with realistic expectations)
  3. Fundamental design quality (most effective safety)

### Related Work
- Circuit Breaker Pattern: Michael Nygard, "Release It!"
- Retry Strategies: AWS Architecture Blog
- Rate Limiting: NGINX rate limiting guide
- LLM Safety: OpenAI, Anthropic safety documentation

### Standards
- Pydantic: Data validation using Python type hints
- JSON Lines: Newline-delimited JSON for logs
- Async/Await: Python asyncio for concurrent operations

---

**Document Version:** 1.0
**Last Updated:** January 14, 2026
**Maintainer:** LLM Guardian Team
