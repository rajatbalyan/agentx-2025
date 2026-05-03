# site_sentry/agents/accessibility_agent.py
"""
Accessibility Agent — fixes WCAG 2.2 AA violations found by Lighthouse.
Handles: ARIA, semantic HTML, keyboard nav, alt text, heading hierarchy, contrast.
"""
from __future__ import annotations
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from site_sentry.core.base_agent import BaseAgent
from site_sentry.config.schema import SentryConfig


SYSTEM_PROMPT = """
You are a senior accessibility engineer with expertise in WCAG 2.2 (AA compliance),
ARIA authoring practices, screen reader behavior, and Lighthouse accessibility audits.

YOUR INPUT will contain:
  - website_url: the live site URL
  - issues: a prioritized list of Lighthouse accessibility audit failures, each with
    id, title, description, severity (high/medium/low), and display_value
  - file_contents: a dict of { "relative/path": "full file content" } for
    the most relevant source files already fetched from the repo

YOUR JOB:
Fix accessibility violations to bring the site closer to WCAG 2.2 AA compliance.
You must:
  1. Fix high-severity issues first — focus on violations that prevent screen reader
     users or keyboard-only users from accessing content.
  2. Only edit files present in file_contents — never invent file paths.
  3. Make conservative, targeted changes — add ARIA attributes, fix roles, and
     correct semantics without restructuring the layout or changing visual design.
  4. Never add ARIA attributes that conflict with the element's native semantics
     (e.g., do not add role="button" to a native <button>, do not add aria-hidden
     to focusable elements that contain meaningful content).
  5. When writing alt text for images, make it descriptive and contextual —
     never use generic text like "image" or repeat the filename.

COMMON FIXES YOU HANDLE:
  - Adding aria-label or aria-labelledby to interactive elements without visible text
  - Adding alt attributes to images (descriptive, contextual text)
  - Adding <label> elements or aria-label to form inputs
  - Fixing insufficient color contrast (note the specific elements affected in reason)
  - Ensuring interactive elements are keyboard focusable (tabindex, role)
  - Adding skip navigation links (<a href="#main">Skip to main content</a>)
  - Fixing heading hierarchy (no skipped levels: h1 → h2 → h3)
  - Adding <html lang="..."> attribute
  - Fixing empty links and buttons (adding discernible text or aria-label)
  - Ensuring lists use proper <ul>/<ol>/<li> semantics

REASONING STEP:
Before writing JSON, think through: which issues are WCAG A or AA violations
(highest priority)? Which can be fixed safely without visual side effects?
Then output ONLY the JSON.

OUTPUT FORMAT — JSON only, no markdown fences, no preamble:
{
  "changes": [
    {
      "path": "relative/path/to/file",
      "content": "COMPLETE new file content — never partial snippets",
      "reason": "Specific fix: e.g. Added aria-label to 4 icon-only buttons, fixed h3 skipping h2 in nav"
    }
  ],
  "summary": "One concise paragraph: WCAG violations fixed, estimated accessibility score improvement, anything skipped"
}

Use "changes": [] if no safe accessibility fixes can be applied.
"""


class AccessibilityAgent(BaseAgent):
    """Fixes Lighthouse accessibility audit failures (WCAG 2.2 AA focus)."""

    llm_role = "agent"

    def __init__(self, config: SentryConfig) -> None:
        super().__init__(config, name="accessibility_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            issues = input_data.get("issues", [])
            file_contents = input_data.get("file_contents", {})
            url = input_data.get("url", "")

            if not issues:
                return self._success_result(
                    changes=[],
                    summary="No accessibility issues to fix.",
                )

            prompt = self._build_prompt(url, issues, file_contents)
            raw = await self._invoke_llm(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )

            result = self._extract_json(raw)
            changes = self._normalize_change_list(result.get("changes"))
            summary = str(result.get("summary", ""))

            self.memory.store(
                {"url": url, "issues_fixed": len(changes)},
                doc_type="accessibility_fix",
            )
            self.logger.info("Accessibility fixes generated", changes=len(changes))
            return self._success_result(changes=changes, summary=summary)

        except Exception as e:
            return self._error_result(e, "AccessibilityAgent.process")

    def _build_prompt(
        self, url: str, issues: List[Dict], file_contents: Dict[str, str]
    ) -> str:
        lines = [
            f"Target website: {url}",
            "",
            "ACCESSIBILITY ISSUES TO FIX:",
        ]

        for i, issue in enumerate(issues[:12], 1):
            severity = issue.get("severity", "?").upper()
            lines.append(f"{i}. [{severity}] {issue.get('title', '')}")
            if issue.get("description"):
                lines.append(f"   Description: {issue['description'][:200]}")
            if issue.get("display_value"):
                lines.append(f"   Current state: {issue['display_value']}")
            if issue.get("details"):
                lines.append(f"   Affected elements: {issue['details'][:150]}")

        if file_contents:
            lines.append("\nRELEVANT SOURCE FILES:")
            for path, content in file_contents.items():
                lines.append(f"\n--- {path} ---")
                lines.append(content[:3000])

        lines.append("\nApply your reasoning step, then output the JSON fixes:")
        return "\n".join(lines)
