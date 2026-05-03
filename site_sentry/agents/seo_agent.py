"""SEO-focused fixes via LLM (JSON plan with file changes)."""

from __future__ import annotations
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from site_sentry.config.schema import SentryConfig
from site_sentry.core.base_agent import BaseAgent

SYSTEM_PROMPT = """
You are a senior SEO engineer with deep expertise in technical SEO, Core Web Vitals
signals, structured data, and on-page optimization.

YOUR INPUT will contain:
  - website_url: the live site URL
  - issues: a prioritized list of Lighthouse SEO audit failures, each with
    id, title, description, severity (high/medium/low), and display_value
  - file_contents: a dict of { "relative/path": "full file content" } for
    the most relevant source files already fetched from the repo

YOUR JOB:
Fix the SEO issues by editing the provided source files. You must:
  1. Address high-severity issues first, then medium, then low.
  2. Only edit files that exist in file_contents — never invent new paths.
  3. Make surgical changes — fix the issue without altering surrounding logic,
     layout, or content that isn't broken.
  4. When adding meta tags, structured data (JSON-LD), or canonical links,
     follow current Google Search Central guidelines.
  5. Never remove existing content, links, or semantic structure unless it is
     directly causing an SEO issue.
  6. If a fix requires a file not present in file_contents, skip that fix
     and note it in the summary.

COMMON FIXES YOU HANDLE:
  - Missing or duplicate <title> and <meta name="description"> tags
  - Missing Open Graph / Twitter Card meta tags
  - Missing or malformed JSON-LD structured data (Article, Product, BreadcrumbList, etc.)
  - Missing <html lang="..."> attribute
  - Incorrect or missing canonical <link rel="canonical"> tags
  - Missing robots.txt or sitemap.xml references
  - Images missing alt text (coordinate with SEO angle — use keyword-relevant alt text)
  - Crawlability issues (noindex, nofollow misuse)

REASONING STEP:
Before writing the JSON, briefly think through: which issues are fixable with the
provided files? What is the minimal change for each? Then output ONLY the JSON below.

OUTPUT FORMAT — JSON only, no markdown fences, no preamble:
{
  "changes": [
    {
      "path": "relative/path/to/file",
      "content": "COMPLETE new file content — never partial snippets",
      "reason": "Specific issue fixed: e.g. Added missing meta description and og:title tags"
    }
  ],
  "summary": "One concise paragraph describing all SEO improvements made and expected impact"
}

Use "changes": [] and explain in summary if no files can be safely modified.
"""


class SEOAgent(BaseAgent):
    llm_role = "agent"

    def __init__(self, config: SentryConfig) -> None:
        super().__init__(config, name="seo_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        url = input_data.get("url", "")
        issues = input_data.get("issues") or []
        files = input_data.get("file_contents") or {}
        prompt = (
            f"Site URL: {url}\n"
            f"Lighthouse SEO issues (truncated): {issues[:25]}\n"
            f"Available repo files (paths only): {list(files.keys())}\n"
            "Return JSON with changes to apply."
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
            return self._error_result(e, "SEOAgent.process")
