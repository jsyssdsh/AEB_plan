"""Anthropic Claude client implementation."""

import time
from datetime import datetime
from typing import Any, Dict

import anthropic

from llm_guardian.core.exceptions import LLMProviderAPIError, LLMProviderTimeoutError
from llm_guardian.core.models import LLMResponse, RequestContext
from llm_guardian.integrations.base import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude API."""

    # Pricing per million tokens (as of January 2025)
    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,
            "output": 15.00,
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,
            "output": 4.00,
        },
        "claude-3-opus-20240229": {
            "input": 15.00,
            "output": 75.00,
        },
    }

    def __init__(self, api_key: str):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
        """
        super().__init__(api_key)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, context: RequestContext, model: str) -> LLMResponse:
        """
        Generate response using Claude.

        Args:
            context: Request context
            model: Model identifier

        Returns:
            LLMResponse

        Raises:
            LLMProviderAPIError: If API call fails
            LLMProviderTimeoutError: If request times out
        """
        try:
            start_time = time.time()

            response = await self.client.messages.create(
                model=model,
                max_tokens=context.max_tokens,
                temperature=context.temperature,
                messages=[{"role": "user", "content": context.prompt}],
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response text
            response_text = response.content[0].text if response.content else ""

            # Calculate cost
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens
            cost_usd = self.estimate_cost(tokens_input, tokens_output, model)

            return LLMResponse(
                request_id=context.request_id,
                response_text=response_text,
                latency_ms=latency_ms,
                tokens_used=tokens_input + tokens_output,
                cost_usd=cost_usd,
                provider="anthropic",
                model=model,
                raw_response={
                    "usage": {
                        "prompt_tokens": tokens_input,
                        "completion_tokens": tokens_output,
                        "total_tokens": tokens_input + tokens_output,
                    },
                    "id": response.id,
                    "type": response.type,
                },
            )

        except anthropic.APITimeoutError as e:
            raise LLMProviderTimeoutError(
                f"Anthropic API timeout: {e}", details={"model": model}
            ) from e
        except Exception as e:
            raise LLMProviderAPIError(
                f"Anthropic API error: {e}", details={"model": model}
            ) from e

    def estimate_cost(self, tokens_prompt: int, tokens_completion: int, model: str) -> float:
        """
        Estimate cost for Claude request.

        Args:
            tokens_prompt: Input tokens
            tokens_completion: Output tokens
            model: Model identifier

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(model, self.PRICING["claude-3-5-sonnet-20241022"])

        input_cost = (tokens_prompt / 1_000_000) * pricing["input"]
        output_cost = (tokens_completion / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"
