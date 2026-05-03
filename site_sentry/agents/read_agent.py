# site_sentry/agents/read_agent.py
"""
ReadAgent — audits the live website and structures findings for the ManagerAgent.

Flow:
1. Run Lighthouse audit on the target URL
2. Normalize scores and issues
3. Generate a structured analysis prompt for the ManagerAgent
4. Store results in memory
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
import structlog

from site_sentry.core.base_agent import BaseAgent
from site_sentry.config.schema import SentryConfig
from site_sentry.auditor.lighthouse import run_audit, LighthouseError

logger = structlog.get_logger()

CRITICAL = 50
POOR = 70
NEEDS_WORK = 85


class ReadAgent(BaseAgent):
    """Audits the target website and structures findings."""

    llm_role = "manager"

    def __init__(self, config: SentryConfig):
        super().__init__(config, name="read_agent")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the audit and return structured findings.

        input_data: {"url": "https://..."} or uses config.website_url
        """
        url = input_data.get("url") or self.config.website_url

        try:
            self.logger.info("Starting website audit", url=url)

            audit_result = run_audit(url)
            scores = audit_result["scores"]
            issues = audit_result["issues"]

            tasks = self._build_task_list(scores, issues)
            summary = self._generate_summary(url, scores, issues)

            self.memory.store(
                {
                    "url": url,
                    "scores": scores,
                    "tasks": tasks,
                    "timestamp": datetime.now().isoformat(),
                },
                doc_type="audit",
            )

            self.logger.info(
                "Audit complete",
                url=url,
                performance=scores["performance"],
                seo=scores["seo"],
                tasks_generated=len(tasks),
            )

            return self._success_result(
                url=url,
                scores=scores,
                issues=issues,
                tasks=tasks,
                summary=summary,
                audit_metadata=audit_result["raw_summary"],
            )

        except LighthouseError as e:
            return self._error_result(e, "Lighthouse audit failed")
        except Exception as e:
            return self._error_result(e, "ReadAgent.process")

    def _build_task_list(
        self, scores: Dict[str, float], issues: Dict[str, List]
    ) -> List[Dict[str, Any]]:
        tasks = []

        task_map = [
            ("performance", "performance_optimization", "performance"),
            ("seo", "seo_optimization", "seo"),
            ("accessibility", "accessibility_fix", "accessibility"),
            ("best_practices", "error_fixing", "best_practices"),
        ]

        for score_key, task_type, issue_key in task_map:
            score = scores.get(score_key, 100)
            if score >= NEEDS_WORK:
                continue

            task_issues = issues.get(issue_key, [])
            high_count = sum(1 for i in task_issues if i["severity"] == "high")

            tasks.append(
                {
                    "type": task_type,
                    "priority": self._priority(score),
                    "score": score,
                    "issue_count": len(task_issues),
                    "high_severity_count": high_count,
                    "issues": task_issues[:10],
                }
            )

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: priority_order.get(t["priority"], 4))
        return tasks

    def _priority(self, score: float) -> str:
        if score < CRITICAL:
            return "critical"
        if score < POOR:
            return "high"
        if score < NEEDS_WORK:
            return "medium"
        return "low"

    def _generate_summary(self, url: str, scores: Dict, issues: Dict) -> str:
        lines = [
            f"Site-Sentry Audit: {url}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "SCORES:",
            f"  Performance : {scores['performance']}/100",
            f"  SEO         : {scores['seo']}/100",
            f"  Accessibility: {scores['accessibility']}/100",
            f"  Best Practices: {scores['best_practices']}/100",
            "",
            "HIGH SEVERITY ISSUES:",
        ]
        for category, category_issues in issues.items():
            high = [i for i in category_issues if i["severity"] == "high"]
            for issue in high[:3]:
                lines.append(f"  [{category.upper()}] {issue['title']}")
                if issue.get("description"):
                    lines.append(f"    → {issue['description'][:120]}")

        if not any(any(i["severity"] == "high" for i in v) for v in issues.values()):
            lines.append("  No high severity issues found!")

        return "\n".join(lines)
