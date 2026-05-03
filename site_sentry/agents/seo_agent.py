"""SEO-focused fixes (stub: returns no file changes until implemented)."""

from __future__ import annotations
from typing import Any, Dict

from site_sentry.config.schema import SentryConfig
from site_sentry.core.base_agent import BaseAgent


class SEOAgent(BaseAgent):
    llm_role = "agent"

    def __init__(self, config: SentryConfig) -> None:
        super().__init__(config, name="seo_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._success_result(
            changes=[],
            summary="SEOAgent: not yet implemented",
        )
