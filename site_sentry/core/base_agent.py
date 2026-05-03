# site_sentry/core/base_agent.py
"""
Base class for all Site-Sentry agents.
- LLM is injected via get_llm() factory (not hardcoded)
- Memory is optional and never crashes the pipeline
- Clean async interface
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

from site_sentry.config.schema import SentryConfig
from site_sentry.core.llm_provider import get_llm, LLMRole
from site_sentry.core.memory import AgentMemory

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base for all Site-Sentry agents."""

    llm_role: LLMRole = "agent"

    def __init__(self, config: SentryConfig, name: str):
        self.config = config
        self.name = name
        self.logger = logger.bind(agent=name)

        self.llm = get_llm(role=self.llm_role, config=config)

        self.memory = AgentMemory(
            agent_name=name,
            db_path=config.memory.vector_store_path,
            enabled=config.memory.enabled,
            collection_prefix=config.memory.collection_prefix,
        )

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method. Must return a dict with at minimum:
        {"status": "success"|"error", ...}
        """
        ...

    async def cleanup(self) -> None:
        pass

    def _error_result(self, error: Exception, context: str = "") -> Dict[str, Any]:
        msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error("Agent error", error=msg)
        return {"status": "error", "error": msg, "agent": self.name}

    def _success_result(self, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "agent": self.name, **kwargs}
