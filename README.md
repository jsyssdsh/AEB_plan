# LLM Guardian

Comprehensive monitoring and safety system for LLM/Agent applications.

## Overview

LLM Guardian is a Python framework that provides enterprise-grade monitoring, safety, and recovery mechanisms for applications using Large Language Models (LLMs) like Claude and GPT. It implements three core principles:

1. **Monitoring as Early Warning** - Identify gaps between assumptions and actual measurements
2. **Recovery Mechanisms** - Enable system restoration after failures
3. **Fundamental Design Quality** - Validation at boundaries, clear contracts, type safety

## Features

### 🔍 Comprehensive Monitoring
- **Quality Monitoring**: Detect hallucinations, harmful content, and off-task responses
- **Performance Tracking**: Monitor latency, token usage, and costs with percentile analysis
- **Anomaly Detection**: Identify unusual patterns in LLM behavior
- **Budget Enforcement**: Track and limit costs per request, session, and user

### 🛡️ Safety Mechanisms
- **Circuit Breaker**: Prevent cascading failures with automatic recovery
- **Rate Limiting**: Multi-level rate limiting (global, per-user, per-session)
- **Input/Output Validation**: Comprehensive validation at all boundaries
- **Content Filtering**: Multi-category safety checking
- **Prompt Injection Detection**: Protect against prompt injection attacks

### 🔄 Recovery Systems
- **Smart Retry**: Exponential backoff with jitter for transient failures
- **State Management**: Checkpoint and recover from failures
- **Graceful Degradation**: Fallback to alternative providers
- **Audit Logging**: Comprehensive audit trail for all operations

## Installation

```bash
# Clone the repository
cd /home/user-jslee/projects/planning

# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"

# For all features
pip install -e ".[all]"
```

## Quick Start

```python
import asyncio
from llm_guardian import LLMGuardian, RequestContext, GuardianConfig

async def main():
    # Initialize with configuration
    config = GuardianConfig()
    guardian = LLMGuardian(config)

    # Create request with explicit constraints
    context = RequestContext(
        request_id="req-001",
        user_id="user-123",
        prompt="Explain quantum computing in simple terms",
        max_tokens=500,
        temperature=0.7,
        max_cost_usd=0.10,  # Budget limit
    )

    # Execute with full monitoring and safety
    response = await guardian.execute_request(
        context,
        provider="anthropic",
        model="claude-3-5-sonnet-20241022"
    )

    print(f"Response: {response.response_text}")
    print(f"Quality Score: {response.quality_score}")
    print(f"Latency: {response.latency_ms}ms")
    print(f"Cost: ${response.cost_usd:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

Key configuration options:

- **Monitoring**: Quality thresholds, performance limits, anomaly detection
- **Safety**: Circuit breaker settings, content filtering, validation rules
- **Rate Limiting**: Request limits, quotas, budget controls
- **Retry Strategy**: Max attempts, backoff parameters, jitter settings

## Architecture

```
Application Layer (Your LLM/Agent code)
    ↓
Safety Wrapper Layer (Circuit breakers, rate limiting, validation)
    ↓
Monitoring Layer (Quality checks, performance tracking, anomaly detection)
    ↓
Recovery Layer (State management, retry logic, audit logging)
```

### Core Components

- **Guardian Orchestrator** (`llm_guardian/core/guardian.py`): Main entry point coordinating all components
- **Quality Monitor** (`llm_guardian/monitoring/quality_monitor.py`): Early warning system for output quality
- **Circuit Breaker** (`llm_guardian/safety/circuit_breaker.py`): Failure prevention and recovery
- **Rate Limiter** (`llm_guardian/safety/rate_limiter.py`): Resource protection
- **Validators** (`llm_guardian/safety/validators.py`): Boundary validation
- **Retry Manager** (`llm_guardian/recovery/retry_manager.py`): Intelligent retry with exponential backoff

## Examples

See the `examples/` directory for more detailed examples:

- `basic_usage.py` - Simple example showing core functionality
- `agent_monitoring.py` - Agent-specific monitoring patterns
- `custom_validators.py` - Creating custom validation rules

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=llm_guardian --cov-report=html

# Run specific test file
pytest tests/unit/test_monitoring/test_quality_monitor.py
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black .

# Lint
ruff check .

# Type checking
mypy llm_guardian
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

For issues and questions, please open an issue on GitHub.
