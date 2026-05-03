# site_sentry/core/base_agent.py
"""
Base class for all Site-Sentry agents.
- LLM is injected via get_llm() factory (not hardcoded)
- Memory is optional and never crashes the pipeline
- Clean async interface
"""
from __future__ import annotations
import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

import structlog

from site_sentry.config.schema import SentryConfig
from site_sentry.core.llm_provider import get_llm, LLMRole
from site_sentry.core.memory import AgentMemory

logger = structlog.get_logger()


def _message_content_text(content: Union[str, list, Any]) -> str:
    """Normalize LangChain message content to a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


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

    def _extract_json(self, text: str) -> dict:
        """
        Robustly extract a JSON object from an LLM response.
        Handles: raw JSON, ```json fences, ``` fences, leading/trailing text.
        """
        text = text.strip()

        fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
        if fenced:
            text = fenced.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        obj_match = re.search(r"\{[\s\S]+\}", text)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not extract valid JSON from LLM response. "
            f"First 300 chars: {text[:300]}"
        )

    async def _invoke_llm(self, messages: list, max_retries: int = 3) -> str:
        """
        Invoke the LLM with automatic retry on transient errors.
        Waits 2s, 4s, 8s between retries (exponential backoff).
        Returns the response content as a string.
        """
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(messages)
                raw = getattr(response, "content", response)
                return _message_content_text(raw)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    self.logger.warning(
                        "LLM call failed, retrying",
                        attempt=attempt + 1,
                        wait_seconds=wait,
                        error=str(e)[:120],
                    )
                    await asyncio.sleep(wait)
        raise RuntimeError(
            f"LLM call failed after {max_retries} attempts: {last_error}"
        )

    def _normalize_change_list(self, raw: Any) -> List[Dict[str, str]]:
        """Parse LLM JSON ``changes`` into GitHub-compatible dicts."""
        if not isinstance(raw, list):
            return []
        out: List[Dict[str, str]] = []
        for c in raw:
            if isinstance(c, dict) and c.get("path") is not None and "content" in c:
                out.append(
                    {
                        "path": str(c["path"]),
                        "content": str(c["content"]),
                        "reason": str(c.get("reason", "")),
                    }
                )
        return out
