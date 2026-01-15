"""
Basic usage example for LLM Guardian.

Demonstrates how to use the monitoring and safety system for LLM applications.
"""

import asyncio
import os
from datetime import datetime

from llm_guardian import GuardianConfig, LLMGuardian, RequestContext


async def main():
    """Main example function."""
    print("=" * 80)
    print("LLM Guardian - Basic Usage Example")
    print("=" * 80)
    print()

    # 1. Initialize Guardian with configuration
    print("1. Initializing LLM Guardian...")
    config = GuardianConfig()

    # Check if API keys are configured
    if not config.anthropic_api_key and not config.openai_api_key:
        print(
            "ERROR: No API keys configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY"
        )
        print("Example: export ANTHROPIC_API_KEY='your-key-here'")
        return

    guardian = LLMGuardian(config)
    print("✓ Guardian initialized")
    print()

    # 2. Create request context with explicit constraints
    print("2. Creating request context...")
    context = RequestContext(
        request_id=f"example-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        user_id="demo-user",
        session_id="demo-session",
        prompt="Explain quantum computing in simple terms",
        max_tokens=500,
        temperature=0.7,
        max_cost_usd=0.10,  # Budget constraint
    )
    print(f"✓ Request ID: {context.request_id}")
    print(f"  User ID: {context.user_id}")
    print(f"  Prompt: {context.prompt}")
    print(f"  Max cost: ${context.max_cost_usd}")
    print()

    # 3. Execute request with full monitoring and safety
    print("3. Executing request with monitoring and safety...")
    try:
        # Choose provider based on available API key
        provider = "anthropic" if config.anthropic_api_key else "openai"
        model = (
            "claude-3-5-sonnet-20241022"
            if provider == "anthropic"
            else "gpt-3.5-turbo"
        )

        print(f"  Provider: {provider}")
        print(f"  Model: {model}")
        print()

        response = await guardian.execute_request(context, provider=provider, model=model)

        print("✓ Request completed successfully!")
        print()

        # 4. Display response and metrics
        print("4. Response and Metrics:")
        print("-" * 80)
        print(f"Response: {response.response_text[:200]}...")
        print()
        print(f"Quality Score: {response.quality_score:.2f}/1.0 ({response.quality_level})")
        print(f"Latency: {response.latency_ms:.0f}ms")
        print(f"Tokens Used: {response.tokens_used}")
        print(f"Cost: ${response.cost_usd:.4f}")
        print()

        # 5. Check for quality issues
        print("5. Quality Checks:")
        print("-" * 80)
        if response.contains_harmful_content:
            print("⚠ WARNING: Harmful content detected")
        else:
            print("✓ No harmful content detected")

        if response.is_hallucination:
            print("⚠ WARNING: Possible hallucination")
        else:
            print("✓ No hallucination detected")

        if response.is_off_task:
            print("⚠ WARNING: Response may be off-task")
        else:
            print("✓ Response is on-task")
        print()

        # 6. Get system status
        print("6. System Status:")
        print("-" * 80)

        # Circuit breaker status
        cb_status = guardian.get_circuit_breaker_status()
        print(f"Circuit Breaker: {cb_status['state'].upper()}")
        print(f"  Total calls: {cb_status['total_calls']}")
        print(f"  Success rate: {(1 - cb_status['failure_rate']) * 100:.1f}%")

        # Rate limiter status
        rl_status = guardian.get_rate_limiter_status(user_id=context.user_id)
        if "user_quota" in rl_status:
            quota = rl_status["user_quota"]
            print(f"User Quota: ${quota['current_usage_usd']:.4f}/${quota['daily_limit_usd']:.2f}")
            print(
                f"  Remaining: ${quota['remaining_usd']:.2f} ({100 - quota['usage_percentage']:.1f}% left)"
            )

        print()

    except Exception as e:
        print(f"✗ Request failed: {type(e).__name__}: {e}")
        print()

    # 7. Get quality trends (if multiple requests have been made)
    print("7. Quality Trends:")
    print("-" * 80)
    trends = guardian.get_quality_trends(window_size=100)
    if trends:
        print(f"Mean quality: {trends['mean_quality']:.2f}")
        print(f"Min quality: {trends['min_quality']:.2f}")
        print(f"Max quality: {trends['max_quality']:.2f}")
        print(f"Sample count: {trends['sample_count']}")
    else:
        print("No quality trend data yet (need multiple requests)")
    print()

    print("=" * 80)
    print("Example completed!")
    print()
    print("Audit logs are available in:", config.audit_log_path)
    print("State checkpoints are in:", config.state_storage_path)
    print("=" * 80)


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
