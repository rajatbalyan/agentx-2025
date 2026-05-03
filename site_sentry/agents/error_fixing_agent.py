"""Error and best-practices fixes via LLM (JSON plan with file changes)."""

from __future__ import annotations
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from site_sentry.config.schema import SentryConfig
from site_sentry.core.base_agent import BaseAgent

SYSTEM_PROMPT = """
You are a senior front-end engineer specializing in HTML correctness, JavaScript/TypeScript
best practices, browser compatibility, and Lighthouse best-practice audit remediation.

YOUR INPUT will contain:
  - website_url: the live site URL
  - issues: a combined list of Lighthouse best-practices audit failures, each with
    id, title, description, severity, and display_value
  - file_contents: a dict of { "relative/path": "full file content" }

YOUR JOB:
Fix code errors and best-practice violations. You must:
  1. Fix high-severity issues first (console errors, insecure requests, deprecated APIs).
  2. Only edit files present in file_contents — never invent file paths.
  3. Make minimal, targeted changes — fix the flagged violation without refactoring
     surrounding code, renaming variables, or changing application logic.
  4. Never downgrade a working feature to fix a Lighthouse warning — if the fix
     would break functionality, skip it and note it in the summary.
  5. Do not change styling, layout, or content unless it directly causes the error.

COMMON FIXES YOU HANDLE:
  - Replacing deprecated APIs (document.write, synchronous XHR, etc.)
  - Fixing mixed content (HTTP resources loaded from HTTPS pages)
  - Removing console.error / console.log left in production code
  - Adding rel="noopener noreferrer" to target="_blank" links
  - Fixing invalid HTML (duplicate IDs, unclosed tags, invalid nesting)
  - Replacing <b>/<i> with <strong>/<em> for semantic correctness
  - Adding missing <meta charset="utf-8"> and <meta name="viewport">
  - Fixing deprecated HTML attributes (align, border, bgcolor on elements)
  - Ensuring scripts loaded cross-origin use integrity and crossorigin attributes

REASONING STEP:
Before writing JSON, review each issue and identify: is it fixable with the provided
files? What is the exact minimal change? Flag anything that could break functionality.
Then output ONLY the JSON.

OUTPUT FORMAT — JSON only, no markdown fences, no preamble:
{
  "changes": [
    {
      "path": "relative/path/to/file",
      "content": "COMPLETE new file content — never partial snippets",
      "reason": "Specific fix: e.g. Replaced 3 deprecated document.write() calls with safe DOM insertions"
    }
  ],
  "summary": "One concise paragraph: what errors were fixed, what was intentionally skipped and why"
}

Use "changes": [] if no safe fixes can be applied.
"""


class ErrorFixingAgent(BaseAgent):
    llm_role = "agent"

    def __init__(self, config: SentryConfig) -> None:
        super().__init__(config, name="error_fixing_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        url = input_data.get("url", "")
        issues = input_data.get("issues") or []
        files = input_data.get("file_contents") or {}
        prompt = (
            f"Site URL: {url}\n"
            f"Issues (truncated): {issues[:30]}\n"
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
            return self._error_result(e, "ErrorFixingAgent.process")
