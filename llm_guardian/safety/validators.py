"""
Input and output validation.

Implements Principle 3: Comprehensive validation at system boundaries.
"""

import re
from typing import List

from pydantic import ValidationError as PydanticValidationError

from llm_guardian.core.config import SafetyConfig
from llm_guardian.core.exceptions import PromptInjectionError, ValidationError
from llm_guardian.core.models import (
    LLMResponse,
    RequestContext,
    ValidationResult,
)


class InputValidator:
    """
    Comprehensive input validation.

    Validates:
    - Schema compliance (via Pydantic)
    - Prompt injection attempts
    - Content length limits
    - Forbidden patterns
    - Topic allowlists
    """

    def __init__(self, config: SafetyConfig):
        """
        Initialize input validator.

        Args:
            config: Safety configuration
        """
        self.config = config

        # Prompt injection patterns
        self.injection_patterns = [
            r"ignore (previous|above|all|any) (instructions?|prompts?|rules?)",
            r"disregard (all|any|the) (previous|prior|above) (instructions?|prompts?)",
            r"(new|updated) (instruction|prompt|task|rule)s?:",
            r"system:?\s*(you are|act as|pretend|simulate)",
            r"<\|im_start\|>|<\|im_end\|>",  # Chat format markers
            r"\[INST\]|\[/INST\]",  # Instruction markers
            r"forget (everything|all|your) (previous|above)",
            r"override (all|previous|safety) (instructions?|settings?|rules?)",
        ]

    async def validate_input(self, context: RequestContext) -> ValidationResult:
        """
        Validate input request comprehensively.

        Args:
            context: Request context

        Returns:
            ValidationResult with validation status

        Raises:
            ValidationError: If validation fails critically
            PromptInjectionError: If prompt injection detected
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # 1. Schema validation (already done by Pydantic at construction)
        # If we got here, schema is valid

        # 2. Prompt injection detection
        injection_detected = self._check_injection(context.prompt)
        if injection_detected:
            result.is_valid = False
            result.errors.append("Potential prompt injection detected")
            result.severity = "high"
            raise PromptInjectionError(
                "Prompt injection attempt detected",
                details={"prompt_preview": context.prompt[:200]},
            )

        # 3. Content length validation
        if len(context.prompt) > self.config.max_prompt_length:
            result.is_valid = False
            result.errors.append(
                f"Prompt exceeds maximum length: {len(context.prompt)} > {self.config.max_prompt_length}"
            )

        # 4. Forbidden pattern checking
        if context.forbidden_patterns:
            for pattern in context.forbidden_patterns:
                if re.search(pattern, context.prompt, re.IGNORECASE):
                    result.is_valid = False
                    result.errors.append(f"Forbidden pattern detected: {pattern}")

        # 5. Topic allowlist validation
        if context.allowed_topics:
            if not self._check_topics(context.prompt, context.allowed_topics):
                result.warnings.append("Prompt topic may not be in allowlist")

        # Raise if validation failed
        if not result.is_valid:
            raise ValidationError(
                f"Input validation failed: {', '.join(result.errors)}",
                details={
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "severity": result.severity,
                },
            )

        return result

    def _check_injection(self, prompt: str) -> bool:
        """
        Check for prompt injection attempts.

        Args:
            prompt: Input prompt

        Returns:
            True if injection pattern detected
        """
        for pattern in self.injection_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        return False

    def _check_topics(self, prompt: str, allowed_topics: List[str]) -> bool:
        """
        Check if prompt is within allowed topics.

        Args:
            prompt: Input prompt
            allowed_topics: List of allowed topics

        Returns:
            True if prompt matches allowed topics
        """
        # Simple keyword matching
        prompt_lower = prompt.lower()
        return any(topic.lower() in prompt_lower for topic in allowed_topics)


class OutputValidator:
    """
    Validate LLM outputs before returning to user.

    Validates:
    - Quality thresholds
    - Safety requirements
    - Hallucination checks
    - Response completeness
    """

    def __init__(self, config: SafetyConfig):
        """
        Initialize output validator.

        Args:
            config: Safety configuration
        """
        self.config = config

    async def validate_output(self, response: LLMResponse) -> ValidationResult:
        """
        Validate output response.

        Args:
            response: LLM response

        Returns:
            ValidationResult

        Raises:
            ValidationError: If validation fails critically
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # 1. Check for harmful content (critical)
        if response.contains_harmful_content:
            result.is_valid = False
            result.errors.append("Response contains harmful content")
            result.severity = "critical"

        # 2. Check quality thresholds
        if response.quality_score < 0.5:
            result.is_valid = False
            result.errors.append(
                f"Response quality too low: {response.quality_score:.2f} < 0.5"
            )
            result.severity = "high"

        # 3. Check for hallucinations
        if response.is_hallucination:
            result.is_valid = False
            result.errors.append("Response likely contains hallucination")
            result.severity = "high"

        # 4. Check for off-task responses
        if response.is_off_task:
            result.warnings.append("Response may be off-task or irrelevant")

        # 5. Length validation
        if len(response.response_text) == 0:
            result.is_valid = False
            result.errors.append("Empty response")
            result.severity = "high"

        # 6. Check for incomplete responses
        if len(response.response_text) < 10:
            result.warnings.append("Response is very short, may be incomplete")

        return result
