"""
LLM Guardian - Comprehensive monitoring and safety system for LLM/Agent applications.

This package provides enterprise-grade monitoring, safety, and recovery mechanisms
for applications using Large Language Models.

Core Principles:
1. Monitoring as Early Warning - Identify gaps between assumptions and actual measurements
2. Recovery Mechanisms - Enable system restoration after failures
3. Fundamental Design Quality - Validation at boundaries, clear contracts, type safety
"""

from llm_guardian.core.guardian import LLMGuardian
from llm_guardian.core.models import RequestContext, LLMResponse, ResponseQuality
from llm_guardian.core.config import GuardianConfig

__version__ = "0.1.0"

__all__ = [
    "LLMGuardian",
    "RequestContext",
    "LLMResponse",
    "ResponseQuality",
    "GuardianConfig",
]
