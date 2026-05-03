"""Performance-focused fixes via LLM (JSON plan with file changes)."""

from __future__ import annotations
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from site_sentry.config.schema import SentryConfig
from site_sentry.core.base_agent import BaseAgent

SYSTEM_PROMPT = """
You are a senior web performance engineer specializing in Core Web Vitals (LCP, CLS, INP),
Lighthouse performance audits, and production-safe optimization techniques.

YOUR INPUT will contain:
  - website_url: the live site URL
  - issues: a prioritized list of Lighthouse performance audit failures, each with
    id, title, description, severity, display_value, and details (affected resources)
  - metrics: a dict of current scores e.g. {"performance": 62, "lcp": "4.2s", ...}
  - file_contents: a dict of { "relative/path": "full file content" }

YOUR JOB:
Improve performance scores by editing the provided source files. You must:
  1. Prioritize changes by impact: LCP and CLS fixes before minor optimizations.
  2. Only edit files that exist in file_contents — never invent paths or assume
     files exist that aren't provided.
  3. Make production-safe changes only — never change business logic, API calls,
     routing, or application state. Only touch rendering, loading, and asset handling.
  4. When adding lazy loading, code splitting, or deferring scripts, verify the
     change won't break above-the-fold rendering.
  5. Do not add new npm dependencies — work with what's already in the codebase.

COMMON FIXES YOU HANDLE:
  - Adding loading="lazy" to below-fold images
  - Adding width/height attributes to images to prevent CLS
  - Moving render-blocking <script> tags to use defer or async
  - Converting @import CSS to <link> tags
  - Adding font-display: swap to @font-face declarations
  - Adding preload hints (<link rel="preload">) for critical assets
  - Removing unused inline styles and scripts
  - Adding fetchpriority="high" to LCP image candidates
  - Implementing responsive images with srcset and sizes

REASONING STEP:
Before writing JSON, think through: given the current scores and the provided files,
which 2-3 changes will have the highest impact on LCP, CLS, and overall score?
Then output ONLY the JSON.

OUTPUT FORMAT — JSON only, no markdown fences, no preamble:
{
  "changes": [
    {
      "path": "relative/path/to/file",
      "content": "COMPLETE new file content — never partial snippets",
      "reason": "Specific optimization: e.g. Added lazy loading to 6 below-fold images, fixes render-blocking LCP"
    }
  ],
  "summary": "One concise paragraph: what was changed, which metrics it targets, and estimated improvement"
}

Use "changes": [] and explain in summary if no safe optimizations can be made.
"""


class PerformanceAgent(BaseAgent):
    llm_role = "agent"

    def __init__(self, config: SentryConfig) -> None:
        super().__init__(config, name="performance_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        url = input_data.get("url", "")
        issues = input_data.get("issues") or []
        metrics = input_data.get("metrics") or {}
        files = input_data.get("file_contents") or {}
        prompt = (
            f"Site URL: {url}\n"
            f"Lighthouse scores: {metrics}\n"
            f"Performance issues (truncated): {issues[:25]}\n"
            f"Available repo files: {list(files.keys())}\n"
            "Return JSON with changes."
        )
        try:
            raw = await self._invoke_llm(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            result = self._extract_json(raw)
            changes = self._normalize_change_list(result.get("changes"))
            return self._success_result(
                changes=changes,
                summary=str(result.get("summary", "")),
            )
        except Exception as e:
            return self._error_result(e, "PerformanceAgent.process")
