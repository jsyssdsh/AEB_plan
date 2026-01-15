"""
Base LLM client interface.

Defines the contract for LLM provider integrations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

from llm_guardian.core.models import LLMResponse, RequestContext


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM provider clients.

    All provider implementations must inherit from this class.
    """

    def __init__(self, api_key: str):
        """
        Initialize LLM client.

        Args:
            api_key: Provider API key
        """
        self.api_key = api_key

    @abstractmethod
    async def generate(self, context: RequestContext, model: str) -> LLMResponse:
        """
        Generate LLM response.

        Args:
            context: Request context
            model: Model identifier

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    def estimate_cost(self, tokens_prompt: int, tokens_completion: int, model: str) -> float:
        """
        Estimate cost for token usage.

        Args:
            tokens_prompt: Prompt tokens
            tokens_completion: Completion tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get provider name.

        Returns:
            Provider name (e.g., "anthropic", "openai")
        """
        pass
