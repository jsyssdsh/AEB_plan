"""
Comprehensive audit logging for all LLM interactions.

Critical for debugging, compliance, and security analysis.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from llm_guardian.core.models import LLMResponse, MonitoringAlert, RequestContext


class AuditLogger:
    """
    Comprehensive audit logging for all LLM interactions.

    Logs all requests, responses, errors, and alerts in structured format.
    """

    def __init__(self, log_dir: Path):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure structured logging
        self.logger = logging.getLogger("llm_guardian.audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # File handler for audit logs (one file per day)
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def log_request(self, context: RequestContext) -> None:
        """
        Log incoming request.

        Args:
            context: Request context
        """
        self._log_event(
            "request",
            {
                "request_id": context.request_id,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "prompt_length": len(context.prompt),
                "prompt_preview": context.prompt[:100] + "..."
                if len(context.prompt) > 100
                else context.prompt,
                "max_tokens": context.max_tokens,
                "temperature": context.temperature,
                "metadata": context.metadata,
            },
        )

    def log_response(self, response: LLMResponse) -> None:
        """
        Log LLM response.

        Args:
            response: LLM response
        """
        self._log_event(
            "response",
            {
                "request_id": response.request_id,
                "response_length": len(response.response_text),
                "response_preview": response.response_text[:100] + "..."
                if len(response.response_text) > 100
                else response.response_text,
                "latency_ms": response.latency_ms,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
                "quality_score": response.quality_score,
                "quality_level": response.quality_level,
                "contains_harmful_content": response.contains_harmful_content,
                "is_hallucination": response.is_hallucination,
                "is_off_task": response.is_off_task,
                "provider": response.provider,
                "model": response.model,
            },
        )

    def log_error(
        self, request_id: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with context.

        Args:
            request_id: Request identifier
            error: Exception that occurred
            context: Additional context
        """
        self._log_event(
            "error",
            {
                "request_id": request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            },
        )

    def log_alert(self, alert: MonitoringAlert) -> None:
        """
        Log monitoring alert.

        Args:
            alert: Monitoring alert
        """
        self._log_event(
            "alert",
            {
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "category": alert.category,
                "message": alert.message,
                "details": alert.details,
                "request_id": alert.request_id,
            },
        )

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log structured event.

        Args:
            event_type: Type of event
            data: Event data
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **data,
        }
        self.logger.info(json.dumps(log_entry))
