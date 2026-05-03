# site_sentry/pipeline.py
"""
Main Site-Sentry pipeline — orchestrates the full run.
ReadAgent → ManagerAgent → GitHubController → PR
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
import structlog

from site_sentry.config.schema import SentryConfig
from site_sentry.agents.read_agent import ReadAgent
from site_sentry.agents.manager_agent import ManagerAgent
from site_sentry.github.controller import GitHubController, GitHubError

logger = structlog.get_logger()


class SentryPipeline:
    """Full end-to-end Site-Sentry pipeline."""

    def __init__(self, config: SentryConfig):
        self.config = config
        self.logger = logger.bind(pipeline="sentry")

        # Initialize GitHub controller if credentials are present
        self.github: Optional[GitHubController] = None
        if config.github_token and config.github.repo_owner and config.github.repo_name:
            self.github = GitHubController(
                token=config.github_token,
                repo_owner=config.github.repo_owner,
                repo_name=config.github.repo_name,
            )
        else:
            self.logger.warning(
                "GitHub not configured — changes will be reported but NOT committed.\n"
                "Set GITHUB_TOKEN and github.repo_owner/repo_name in your config."
            )

        # Initialize agents
        self.read_agent = ReadAgent(config)
        self.manager_agent = ManagerAgent(config, github=self.github)

    async def run(self, url: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a full pipeline run.

        Args:
            url: Override the website URL from config
            dry_run: If True, generate changes but don't commit/PR

        Returns:
            Pipeline result summary
        """
        target_url = url or self.config.website_url
        self.logger.info("Pipeline starting", url=target_url, dry_run=dry_run)
        start_time = datetime.now()

        # ── Step 1: Audit ─────────────────────────────────────────────────
        self.logger.info("Step 1/4: Running Lighthouse audit...")
        read_result = await self.read_agent.process({"url": target_url})

        if read_result.get("status") != "success":
            return self._failed(f"Audit failed: {read_result.get('error')}", start_time)

        scores = read_result.get("scores", {})
        self.logger.info(
            "Audit complete",
            performance=scores.get("performance"),
            seo=scores.get("seo"),
            tasks=len(read_result.get("tasks", [])),
        )

        # ── Step 2: Plan + Fix ────────────────────────────────────────────
        self.logger.info("Step 2/4: Running specialized agents...")
        manager_result = await self.manager_agent.process(read_result)

        all_changes = manager_result.get("all_changes", [])
        self.logger.info("Agents complete", changes=len(all_changes))

        if not all_changes:
            return {
                "status": "success",
                "message": "No changes needed — your site is in great shape!",
                "scores": scores,
                "duration_seconds": (datetime.now() - start_time).seconds,
            }

        # ── Step 3: Create Branch & Commit ────────────────────────────────
        if dry_run or not self.github:
            mode = "dry-run" if dry_run else "no-github"
            self.logger.info(f"Skipping commit ({mode})", changes=len(all_changes))
            return self._report(
                read_result,
                manager_result,
                pr_result=None,
                mode=mode,
                start_time=start_time,
            )

        self.logger.info("Step 3/4: Creating branch and committing fixes...")
        branch_name = GitHubController.generate_branch_name(
            self.config.github.branch_prefix
        )

        try:
            self.github.create_branch(
                branch_name=branch_name,
                base_branch=self.config.github.base_branch,
            )

            commit_results = self.github.commit_files(
                changes=all_changes,
                branch=branch_name,
                commit_message_prefix="fix(sentry)",
            )
            self.logger.info(
                "Files committed", count=len(commit_results), branch=branch_name
            )

        except GitHubError as e:
            return self._failed(f"GitHub error during commit: {e}", start_time)

        # ── Step 4: Open PR ────────────────────────────────────────────────
        self.logger.info("Step 4/4: Opening pull request...")
        pr_body = self._build_pr_body(scores, manager_result)

        try:
            pr_result = self.github.create_pull_request(
                branch_name=branch_name,
                title=f"🤖 Site-Sentry: Automated fixes ({len(all_changes)} files)",
                body=pr_body,
                base_branch=self.config.github.base_branch,
                labels=self.config.github.pr_labels,
            )
            self.logger.info("PR created", url=pr_result["url"])
        except GitHubError as e:
            return self._failed(f"GitHub PR creation failed: {e}", start_time)

        return self._report(
            read_result, manager_result, pr_result, "committed", start_time
        )

    def _build_pr_body(self, scores: Dict[str, Any], manager_result: Dict[str, Any]) -> str:
        lines = [
            "## 🤖 Site-Sentry Automated Fixes",
            "",
            "### Lighthouse Scores",
            "| Category | Score |",
            "|----------|-------|",
        ]
        for k, v in scores.items():
            emoji = "✅" if v >= 90 else "⚠️" if v >= 70 else "🔴"
            lines.append(f"| {k.replace('_', ' ').title()} | {emoji} {v}/100 |")

        lines.extend(["", "### Changes Made", ""])
        for agent, summary in manager_result.get("summaries", {}).items():
            if summary:
                lines.append(f"**{agent.replace('_', ' ').title()}**")
                lines.append(summary)
                lines.append("")

        changes = manager_result.get("all_changes", [])
        if changes:
            lines.extend(["### Files Modified", ""])
            for c in changes:
                reason = (c.get("reason") or "")[:80]
                lines.append(f"- `{c.get('path')}` — {reason}")

        lines.extend(
            [
                "",
                "---",
                "*Generated by [Site-Sentry](https://github.com/rajatbalyan/agentx-2025)*",
                "*Powered by NVIDIA NIM free tier (DeepSeek V3.2 + V4-Flash)*",
            ]
        )
        return "\n".join(lines)

    def _report(
        self,
        read_result: Dict[str, Any],
        manager_result: Dict[str, Any],
        pr_result: Optional[Dict[str, Any]],
        mode: str,
        start_time: datetime,
    ) -> Dict[str, Any]:
        duration = (datetime.now() - start_time).seconds
        return {
            "status": "success",
            "mode": mode,
            "url": read_result.get("url"),
            "scores": read_result.get("scores"),
            "agents_run": manager_result.get("agents_run", []),
            "changes": len(manager_result.get("all_changes", [])),
            "pr": pr_result,
            "duration_seconds": duration,
        }

    def _failed(self, error: str, start_time: datetime) -> Dict[str, Any]:
        self.logger.error("Pipeline failed", error=error)
        return {
            "status": "error",
            "error": error,
            "duration_seconds": (datetime.now() - start_time).seconds,
        }
