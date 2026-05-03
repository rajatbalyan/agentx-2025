# site_sentry/agents/manager_agent.py
"""
ManagerAgent — LangGraph-based orchestrator for all specialized agents.
Properly uses add_conditional_edges() and wires all 5 specialized agents.
"""
from __future__ import annotations
import asyncio
from typing import Annotated, Any, Dict, List, Optional, TypedDict

import structlog
from langgraph.graph import StateGraph, START, END

from site_sentry.config.schema import SentryConfig
from site_sentry.core.memory import AgentMemory
from site_sentry.agents.seo_agent import SEOAgent
from site_sentry.agents.performance_agent import PerformanceAgent
from site_sentry.agents.error_fixing_agent import ErrorFixingAgent
from site_sentry.agents.content_update_agent import ContentUpdateAgent
from site_sentry.agents.content_generation_agent import ContentGenerationAgent
from site_sentry.github.controller import GitHubController

logger = structlog.get_logger()


# ── LangGraph State ───────────────────────────────────────────────────────────


def _merge_agent_results(
    left: List[Dict[str, Any]], right: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Reducer: concatenate agent result batches (LangGraph state merge)."""
    if not left:
        return list(right) if right else []
    if not right:
        return list(left)
    return list(left) + list(right)


class PipelineState(TypedDict, total=False):
    """Shared state flowing through the LangGraph workflow."""

    url: str
    scores: Dict[str, float]
    issues: Dict[str, List[Dict[str, Any]]]
    tasks: List[Dict[str, Any]]
    active_agents: List[str]
    file_contents: Dict[str, str]
    agent_results: Annotated[List[Dict[str, Any]], _merge_agent_results]
    all_changes: List[Dict[str, Any]]
    error: Optional[str]
    branch_name: str


# ── ManagerAgent ──────────────────────────────────────────────────────────────


class ManagerAgent:
    """
    Orchestrates specialized agents using a LangGraph state machine.

    Graph flow:
      START → plan → fetch_files → run_agents → collect → END
    """

    # Map task types to agent names
    TASK_TO_AGENT = {
        "seo_optimization": "seo",
        "performance_optimization": "performance",
        "error_fixing": "error_fixing",
        "accessibility_fix": "error_fixing",  # handled by error agent
        "content_update": "content_update",
        "content_generation": "content_generation",
    }

    # Common file paths to fetch per agent type
    AGENT_FILE_PATTERNS = {
        "seo": [
            "index.html",
            "public/index.html",
            "src/index.html",
            "src/App.jsx",
            "src/App.tsx",
            "pages/index.tsx",
            "robots.txt",
            "sitemap.xml",
        ],
        "performance": [
            "index.html",
            "public/index.html",
            "src/index.js",
            "src/index.ts",
            "next.config.js",
            "next.config.mjs",
            "webpack.config.js",
            "vite.config.js",
        ],
        "error_fixing": [
            "index.html",
            "public/index.html",
            "src/index.html",
            "src/App.jsx",
            "src/App.tsx",
        ],
        "content_update": [
            "index.html",
            "src/App.jsx",
            "src/App.tsx",
            "pages/index.tsx",
            "content/index.md",
        ],
        "content_generation": [
            "index.html",
            "src/App.jsx",
            "src/App.tsx",
        ],
    }

    def __init__(self, config: SentryConfig, github: Optional[GitHubController] = None):
        self.config = config
        self.github = github
        self.logger = logger.bind(agent="manager_agent")
        self.memory = AgentMemory(
            agent_name="manager_agent",
            db_path=config.memory.vector_store_path,
            enabled=config.memory.enabled,
            collection_prefix=config.memory.collection_prefix,
        )

        # Initialize all specialized agents
        self.agents = {
            "seo": SEOAgent(config),
            "performance": PerformanceAgent(config),
            "error_fixing": ErrorFixingAgent(config),
            "content_update": ContentUpdateAgent(config),
            "content_generation": ContentGenerationAgent(config),
        }

        # Build the LangGraph workflow
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the LangGraph state machine."""
        g = StateGraph(PipelineState)

        g.add_node("plan", self._plan)
        g.add_node("fetch_files", self._fetch_files)
        g.add_node("run_agents", self._run_agents)
        g.add_node("collect", self._collect)

        g.add_edge(START, "plan")

        def route_after_plan(state: PipelineState) -> str:
            if state.get("active_agents"):
                return "fetch_files"
            return "collect"

        g.add_conditional_edges("plan", route_after_plan, {"fetch_files": "fetch_files", "collect": "collect"})
        g.add_edge("fetch_files", "run_agents")
        g.add_edge("run_agents", "collect")
        g.add_edge("collect", END)

        return g.compile()

    # ── Graph Nodes ───────────────────────────────────────────────────────────

    async def _plan(self, state: PipelineState) -> Dict[str, Any]:
        """Decide which agents to run based on scores and config toggles."""
        tasks = state.get("tasks", [])
        agent_config = self.config.agents

        active: List[str] = []
        for task in tasks:
            task_type = task.get("type", "")
            agent_name = self.TASK_TO_AGENT.get(task_type)
            if not agent_name:
                continue

            # Check if agent is enabled in config
            enabled_map = {
                "seo": agent_config.seo,
                "performance": agent_config.performance,
                "error_fixing": agent_config.error_fixing,
                "content_update": agent_config.content_update,
                "content_generation": agent_config.content_generation,
            }

            if enabled_map.get(agent_name, False) and agent_name not in active:
                active.append(agent_name)
                self.logger.info(
                    "Agent scheduled",
                    agent=agent_name,
                    task=task_type,
                    priority=task.get("priority"),
                )

        if not active:
            self.logger.info("No agents needed — all scores are good!")

        return {"active_agents": active}

    async def _fetch_files(self, state: PipelineState) -> Dict[str, Any]:
        """Fetch relevant source files from GitHub for active agents."""
        if not self.github:
            self.logger.info("No GitHub controller — skipping file fetch")
            return {"file_contents": {}}

        active_agents = state.get("active_agents", [])
        branch = self.config.github.base_branch
        fetched: Dict[str, str] = {}

        # Collect unique file paths needed by all active agents
        paths_needed: set[str] = set()
        for agent_name in active_agents:
            patterns = self.AGENT_FILE_PATTERNS.get(agent_name, [])
            paths_needed.update(patterns)

        for path in paths_needed:
            try:
                file_data = self.github.get_file(path, branch)
                if file_data:
                    fetched[path] = file_data["content"]
                    self.logger.debug("Fetched file", path=path)
            except Exception as e:
                self.logger.debug("File not found (skipping)", path=path, error=str(e))

        self.logger.info("Files fetched", count=len(fetched))
        return {"file_contents": fetched}

    async def _run_agents(self, state: PipelineState) -> Dict[str, Any]:
        """Run all active specialized agents (concurrently where safe)."""
        active_agents = state.get("active_agents", [])
        file_contents = state.get("file_contents", {})
        issues = state.get("issues", {})
        url = state.get("url", "")

        results: List[Dict[str, Any]] = []

        # Build input for each agent
        agent_inputs = {
            "seo": {
                "url": url,
                "issues": issues.get("seo", []),
                "file_contents": file_contents,
            },
            "performance": {
                "url": url,
                "issues": issues.get("performance", []),
                "metrics": state.get("scores", {}),
                "file_contents": file_contents,
            },
            "error_fixing": {
                "url": url,
                "issues": issues.get("best_practices", [])
                + issues.get("accessibility", []),
                "file_contents": file_contents,
            },
            "content_update": {
                "url": url,
                "file_contents": file_contents,
            },
            "content_generation": {
                "url": url,
                "gaps": [
                    i.get("title", "")
                    for i in issues.get("seo", [])
                    if "missing" in i.get("title", "").lower()
                ],
                "file_contents": file_contents,
            },
        }

        # Run each agent sequentially (to respect 40 RPM rate limit)
        for i, agent_name in enumerate(active_agents):
            if i > 0:
                # 40 RPM safety margin (~1.5s between LLM-backed agent calls)
                await asyncio.sleep(1.5)

            agent = self.agents.get(agent_name)
            if not agent:
                continue

            self.logger.info("Running agent", agent=agent_name)
            try:
                agent_input = agent_inputs.get(agent_name, {"url": url})
                result = await agent.process(agent_input)
                results.append(
                    {
                        "agent": agent_name,
                        "status": result.get("status"),
                        "changes": result.get("changes", []),
                        "summary": result.get("summary", ""),
                        "error": result.get("error"),
                    }
                )
                self.logger.info(
                    "Agent complete",
                    agent=agent_name,
                    changes=len(result.get("changes", [])),
                    status=result.get("status"),
                )
            except Exception as e:
                self.logger.error("Agent failed", agent=agent_name, error=str(e))
                results.append(
                    {
                        "agent": agent_name,
                        "status": "error",
                        "error": str(e),
                        "changes": [],
                    }
                )

        return {"agent_results": results}

    async def _collect(self, state: PipelineState) -> Dict[str, Any]:
        """Collect all file changes from agent results, deduplicate."""
        agent_results = state.get("agent_results", [])
        all_changes: Dict[str, Dict[str, Any]] = {}

        for result in agent_results:
            for change in result.get("changes", []) or []:
                path = change.get("path")
                if path:
                    # Last agent to touch a file wins (they run in priority order)
                    all_changes[str(path)] = change

        changes_list = list(all_changes.values())
        self.logger.info(
            "Changes collected",
            total=len(changes_list),
            files=[c.get("path") for c in changes_list],
        )

        self.memory.store(
            {
                "url": state.get("url"),
                "agents_run": [r.get("agent") for r in agent_results],
                "total_changes": len(changes_list),
            },
            doc_type="pipeline_run",
        )

        return {"all_changes": changes_list}

    # ── Public API ────────────────────────────────────────────────────────────

    async def process(self, read_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Takes ReadAgent output, returns all file changes.
        """
        if read_result.get("status") != "success":
            return {
                "status": "error",
                "error": "ReadAgent did not succeed",
                "changes": [],
            }

        initial_state: PipelineState = {
            "url": read_result.get("url", ""),
            "scores": read_result.get("scores", {}),
            "issues": read_result.get("issues", {}),
            "tasks": read_result.get("tasks", []),
            "active_agents": [],
            "file_contents": {},
            "agent_results": [],
            "all_changes": [],
            "error": None,
            "branch_name": "",
        }

        final_state = await self._graph.ainvoke(initial_state)

        return {
            "status": "success",
            "url": final_state.get("url", ""),
            "agents_run": [
                r.get("agent")
                for r in final_state.get("agent_results", [])
                if isinstance(r, dict)
            ],
            "all_changes": final_state.get("all_changes", []),
            "summaries": {
                r.get("agent", ""): r.get("summary", "")
                for r in final_state.get("agent_results", [])
                if isinstance(r, dict)
            },
        }
