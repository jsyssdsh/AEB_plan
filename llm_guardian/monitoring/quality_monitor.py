"""
Quality monitoring for LLM responses.

Implements Principle 1: Monitoring as early warning system to identify
gaps between assumptions and actual measurements.
"""

import re
from collections import deque
from typing import Dict, List, Optional, Set

import numpy as np

from llm_guardian.core.config import MonitoringConfig
from llm_guardian.core.exceptions import QualityCheckFailedError
from llm_guardian.core.models import (
    LLMResponse,
    MonitoringAlert,
    QualityAssessment,
    RequestContext,
    ResponseQuality,
)


class HallucinationDetector:
    """
    Detect potential hallucinations in LLM responses.

    Uses pattern matching and heuristics to identify common hallucination markers.
    """

    def __init__(self, threshold: float = 0.7):
        """
        Initialize hallucination detector.

        Args:
            threshold: Probability threshold above which to flag hallucinations
        """
        self.threshold = threshold

        # Patterns that often indicate hallucinations or uncertainty
        self.hallucination_patterns = [
            r"I apologize,?\s+but I (don't|do not|cannot|can't) (actually|really)",
            r"I (made up|invented|fabricated)",
            r"I (don't|do not) have access to",
            r"As an AI( language model)?,?\s+I (can't|cannot|am unable to)",
            r"I (don't|do not) have (real-time )?information",
            r"my (training|knowledge) (data )?(cut-off|cutoff)",
            r"I'm not (sure|certain|confident)",
            r"I (may|might) be (wrong|incorrect|mistaken)",
        ]

    def detect(self, response: LLMResponse) -> float:
        """
        Detect hallucination probability in response.

        Args:
            response: LLM response to check

        Returns:
            Probability score between 0.0 and 1.0
        """
        # Pattern-based detection
        pattern_score = self._check_patterns(response.response_text)

        # Length-based heuristic (very short responses are often uncertain)
        length_score = self._check_length(response.response_text)

        # Weighted combination
        combined_score = 0.7 * pattern_score + 0.3 * length_score

        return min(combined_score, 1.0)

    def _check_patterns(self, text: str) -> float:
        """
        Check for hallucination indicator patterns.

        Args:
            text: Response text

        Returns:
            Score based on pattern matches
        """
        matches = sum(
            1 for pattern in self.hallucination_patterns if re.search(pattern, text, re.IGNORECASE)
        )

        # Each match increases score by 0.3, capped at 1.0
        return min(matches * 0.3, 1.0)

    def _check_length(self, text: str) -> float:
        """
        Check if response is suspiciously short.

        Args:
            text: Response text

        Returns:
            Score based on length
        """
        word_count = len(text.split())

        if word_count < 5:
            return 0.5
        elif word_count < 10:
            return 0.2
        else:
            return 0.0


class ContentSafetyChecker:
    """
    Multi-layered content safety checking for harmful content.

    Checks for:
    - Violence
    - Hate speech
    - Self-harm content
    - Sexual content
    - Illegal activity
    """

    def __init__(self):
        """Initialize content safety checker."""
        self.harmful_categories = {
            "violence": [
                r"\b(kill|murder|assault|attack|weapon|gun|knife|bomb)\b",
                r"\b(hurt|harm|injure|wound)\b",
            ],
            "hate_speech": [
                r"\b(hate|racist|sexist|homophobic|xenophobic)\b",
                r"\b(slur|derogatory|discriminat)\w*\b",
            ],
            "self_harm": [
                r"\b(suicide|self[- ]harm|cut(ting)? (myself|yourself))\b",
                r"\b(end (my|your) life|kill (myself|yourself))\b",
            ],
            "sexual_content": [
                r"\b(explicit|pornograph|sexual)\b.*\b(content|material)\b",
            ],
            "illegal_activity": [
                r"\b(illegal|unlawful|criminal)\b.*\b(activity|action)\b",
                r"\b(hack|exploit|steal|fraud)\b",
            ],
        }

    def check_safety(self, response: LLMResponse) -> Dict[str, any]:
        """
        Comprehensive safety check on response.

        Args:
            response: LLM response to check

        Returns:
            Dictionary with safety check results
        """
        results = {"is_safe": True, "violations": [], "risk_score": 0.0, "details": {}}

        # Pattern-based detection for each category
        for category, patterns in self.harmful_categories.items():
            score = self._check_category(response.response_text, patterns)
            results["details"][category] = score

            if score > 0.5:
                results["is_safe"] = False
                results["violations"].append(category)
                results["risk_score"] = max(results["risk_score"], score)

        return results

    def _check_category(self, text: str, patterns: List[str]) -> float:
        """
        Check text against category patterns.

        Args:
            text: Text to check
            patterns: List of regex patterns

        Returns:
            Risk score for category
        """
        matches = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))

        # Each match increases score
        return min(matches * 0.4, 1.0)


class OffTaskDetector:
    """Detect when LLM response is off-task or irrelevant to the prompt."""

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize off-task detector.

        Args:
            similarity_threshold: Threshold for keyword overlap
        """
        self.similarity_threshold = similarity_threshold

    def detect(self, response: LLMResponse, context: RequestContext) -> bool:
        """
        Check if response is off-task.

        Args:
            response: LLM response
            context: Request context with prompt

        Returns:
            True if response is off-task
        """
        # Extract keywords from prompt and response
        prompt_keywords = self._extract_keywords(context.prompt)
        response_keywords = self._extract_keywords(response.response_text)

        if not prompt_keywords:
            return False

        # Calculate overlap
        overlap = len(prompt_keywords & response_keywords) / len(prompt_keywords)

        return overlap < self.similarity_threshold

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract keywords from text.

        Args:
            text: Input text

        Returns:
            Set of keywords
        """
        # Simple keyword extraction (lowercase, remove common words)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
        }

        words = re.findall(r"\b[a-z]+\b", text.lower())
        keywords = {word for word in words if word not in stop_words and len(word) > 3}

        return keywords


class QualityMonitor:
    """
    Main quality monitoring coordinator.

    Implements Principle 1: Monitoring as early warning system.
    Combines multiple quality checks to assess LLM response quality.
    """

    def __init__(self, config: MonitoringConfig):
        """
        Initialize quality monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config

        # Initialize detectors
        self.hallucination_detector = HallucinationDetector()
        self.safety_checker = ContentSafetyChecker()
        self.off_task_detector = OffTaskDetector()

        # Track quality trends over time
        self.quality_history: deque = deque(maxlen=1000)

        # Alert tracking
        self.active_alerts: List[MonitoringAlert] = []

    async def assess_quality(
        self, response: LLMResponse, context: RequestContext
    ) -> QualityAssessment:
        """
        Comprehensive quality assessment with early warning signals.

        Args:
            response: LLM response to assess
            context: Request context

        Returns:
            QualityAssessment with detailed results

        Raises:
            QualityCheckFailedError: If quality is critically low
        """
        assessment = QualityAssessment(request_id=response.request_id)

        # 1. Check for hallucinations
        hallucination_score = self.hallucination_detector.detect(response)
        assessment.hallucination_probability = hallucination_score
        response.is_hallucination = hallucination_score > 0.7

        # 2. Check content safety
        safety_results = self.safety_checker.check_safety(response)
        response.contains_harmful_content = not safety_results["is_safe"]
        assessment.safety_violations = safety_results["violations"]

        # 3. Check if off-task
        response.is_off_task = self.off_task_detector.detect(response, context)

        # 4. Calculate overall quality score
        quality_score = self._calculate_quality_score(
            hallucination_score=hallucination_score,
            safety_risk=safety_results["risk_score"],
            is_off_task=response.is_off_task,
            response_length=len(response.response_text),
        )

        response.quality_score = quality_score
        response.quality_level = self._categorize_quality(quality_score)

        # Set assessment fields
        assessment.coherence_score = 1.0 - hallucination_score
        assessment.relevance_score = 0.0 if response.is_off_task else 1.0

        # 5. Track for trend analysis
        self.quality_history.append(quality_score)

        # 6. Determine validation status and recommendations
        assessment.pass_validation = self._should_pass_validation(
            quality_score=quality_score,
            safety_violations=assessment.safety_violations,
            is_hallucination=response.is_hallucination,
        )

        assessment.recommended_action = self._recommend_action(
            quality_score=quality_score,
            pass_validation=assessment.pass_validation,
            safety_violations=assessment.safety_violations,
        )

        # Add warnings
        assessment.warnings = self._generate_warnings(
            hallucination_score=hallucination_score,
            safety_risk=safety_results["risk_score"],
            is_off_task=response.is_off_task,
            quality_score=quality_score,
        )

        # 7. Generate alerts if needed
        if quality_score < self.config.quality_alert_threshold:
            await self._raise_quality_alert(response, assessment)

        # 8. Check for critical failures
        if not assessment.pass_validation and quality_score < 0.3:
            raise QualityCheckFailedError(
                f"Quality check failed: score {quality_score:.2f} below critical threshold",
                details={
                    "quality_score": quality_score,
                    "violations": assessment.safety_violations,
                    "warnings": assessment.warnings,
                },
            )

        return assessment

    def _calculate_quality_score(
        self,
        hallucination_score: float,
        safety_risk: float,
        is_off_task: bool,
        response_length: int,
    ) -> float:
        """
        Calculate overall quality score.

        Args:
            hallucination_score: Hallucination probability
            safety_risk: Safety risk score
            is_off_task: Whether response is off-task
            response_length: Length of response text

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Start with perfect score
        base_score = 1.0

        # Penalize hallucination
        base_score -= hallucination_score * 0.4

        # Heavily penalize safety issues
        base_score -= safety_risk * 0.5

        # Penalize off-task responses
        if is_off_task:
            base_score *= 0.5

        # Penalize very short responses (likely incomplete)
        if response_length < 50:
            base_score *= 0.8

        return max(0.0, base_score)

    def _categorize_quality(self, quality_score: float) -> ResponseQuality:
        """
        Categorize quality score into enum.

        Args:
            quality_score: Numeric quality score

        Returns:
            ResponseQuality enum value
        """
        if quality_score >= 0.9:
            return ResponseQuality.EXCELLENT
        elif quality_score >= 0.75:
            return ResponseQuality.GOOD
        elif quality_score >= 0.6:
            return ResponseQuality.ACCEPTABLE
        elif quality_score >= 0.3:
            return ResponseQuality.POOR
        else:
            return ResponseQuality.UNSAFE

    def _should_pass_validation(
        self,
        quality_score: float,
        safety_violations: List[str],
        is_hallucination: bool,
    ) -> bool:
        """
        Determine if response should pass validation.

        Args:
            quality_score: Overall quality score
            safety_violations: List of safety violations
            is_hallucination: Whether response is a hallucination

        Returns:
            True if response passes validation
        """
        # Fail if safety violations
        if safety_violations:
            return False

        # Fail if likely hallucination
        if is_hallucination:
            return False

        # Fail if quality too low
        if quality_score < 0.5:
            return False

        return True

    def _recommend_action(
        self,
        quality_score: float,
        pass_validation: bool,
        safety_violations: List[str],
    ) -> str:
        """
        Recommend action based on assessment.

        Args:
            quality_score: Overall quality score
            pass_validation: Whether response passed validation
            safety_violations: Safety violations

        Returns:
            Recommended action: "accept", "reject", "review", or "fallback"
        """
        if safety_violations:
            return "reject"

        if not pass_validation:
            if quality_score < 0.3:
                return "fallback"
            else:
                return "review"

        if quality_score >= 0.75:
            return "accept"
        else:
            return "review"

    def _generate_warnings(
        self,
        hallucination_score: float,
        safety_risk: float,
        is_off_task: bool,
        quality_score: float,
    ) -> List[str]:
        """
        Generate quality warnings.

        Args:
            hallucination_score: Hallucination probability
            safety_risk: Safety risk score
            is_off_task: Whether response is off-task
            quality_score: Overall quality score

        Returns:
            List of warning messages
        """
        warnings = []

        if hallucination_score > 0.5:
            warnings.append(f"High hallucination probability: {hallucination_score:.2f}")

        if safety_risk > 0.3:
            warnings.append(f"Potential safety concerns: risk score {safety_risk:.2f}")

        if is_off_task:
            warnings.append("Response may be off-task or irrelevant")

        if quality_score < 0.6:
            warnings.append(f"Low quality score: {quality_score:.2f}")

        return warnings

    async def _raise_quality_alert(
        self, response: LLMResponse, assessment: QualityAssessment
    ) -> None:
        """
        Raise monitoring alert for quality issue.

        Args:
            response: LLM response
            assessment: Quality assessment
        """
        alert = MonitoringAlert(
            alert_id=f"alert-quality-{response.request_id}",
            severity="high" if response.quality_score < 0.3 else "medium",
            category="quality",
            message=f"Quality score {response.quality_score:.2f} below threshold {self.config.quality_alert_threshold:.2f}",
            details={
                "quality_score": response.quality_score,
                "quality_level": response.quality_level,
                "hallucination_probability": assessment.hallucination_probability,
                "safety_violations": assessment.safety_violations,
                "warnings": assessment.warnings,
            },
            request_id=response.request_id,
        )

        self.active_alerts.append(alert)

    def get_quality_trends(self, window_size: int = 100) -> Dict[str, float]:
        """
        Get quality trend statistics.

        Args:
            window_size: Number of recent samples to analyze

        Returns:
            Dictionary with trend statistics
        """
        if not self.quality_history:
            return {}

        recent_scores = list(self.quality_history)[-window_size:]

        return {
            "mean_quality": float(np.mean(recent_scores)),
            "std_quality": float(np.std(recent_scores)),
            "min_quality": float(np.min(recent_scores)),
            "max_quality": float(np.max(recent_scores)),
            "p50_quality": float(np.percentile(recent_scores, 50)),
            "p95_quality": float(np.percentile(recent_scores, 95)),
            "sample_count": len(recent_scores),
        }
