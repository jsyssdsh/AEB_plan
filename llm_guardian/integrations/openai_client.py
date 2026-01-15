"""OpenAI GPT client implementation."""

import time
from datetime import datetime
from typing import Any, Dict

import openai

from llm_guardian.core.exceptions import LLMProviderAPIError, LLMProviderTimeoutError
from llm_guardian.core.models import LLMResponse, RequestContext
from llm_guardian.integrations.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI GPT API."""

    # Pricing per million tokens (as of January 2025)
    PRICING = {
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00,
        },
        "gpt-4": {
            "input": 30.00,
            "output": 60.00,
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50,
        },
    }

    def __init__(self, api_key: str):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
        """
        super().__init__(api_key)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(self, context: RequestContext, model: str) -> LLMResponse:
        """
        Generate response using GPT.

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

            response = await self.client.chat.completions.create(
                model=model,
                max_tokens=context.max_tokens,
                temperature=context.temperature,
                messages=[{"role": "user", "content": context.prompt}],
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response text
            response_text = (
                response.choices[0].message.content if response.choices else ""
            )

            # Calculate cost
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            cost_usd = self.estimate_cost(tokens_input, tokens_output, model)

            return LLMResponse(
                request_id=context.request_id,
                response_text=response_text or "",
                latency_ms=latency_ms,
                tokens_used=tokens_input + tokens_output,
                cost_usd=cost_usd,
                provider="openai",
                model=model,
                raw_response={
                    "usage": {
                        "prompt_tokens": tokens_input,
                        "completion_tokens": tokens_output,
                        "total_tokens": tokens_input + tokens_output,
                    },
                    "id": response.id,
                    "object": response.object,
                },
            )

        except openai.APITimeoutError as e:
            raise LLMProviderTimeoutError(
                f"OpenAI API timeout: {e}", details={"model": model}
            ) from e
        except Exception as e:
            raise LLMProviderAPIError(
                f"OpenAI API error: {e}", details={"model": model}
            ) from e

    def estimate_cost(self, tokens_prompt: int, tokens_completion: int, model: str) -> float:
        """
        Estimate cost for GPT request.

        Args:
            tokens_prompt: Input tokens
            tokens_completion: Output tokens
            model: Model identifier

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(model, self.PRICING["gpt-3.5-turbo"])

        input_cost = (tokens_prompt / 1_000_000) * pricing["input"]
        output_cost = (tokens_completion / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openai"
