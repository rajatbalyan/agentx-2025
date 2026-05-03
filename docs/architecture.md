# Architecture

## End-to-end flow

```text
sentry run
    │
    ▼
SentryPipeline.run()
    │
    ├─► ReadAgent.process()
    │       Lighthouse CLI (JSON) → scores, issues, tasks, summary
    │       optional Chroma store (AgentMemory)
    │
    ├─► ManagerAgent.process(read_result)
    │       LangGraph: plan → fetch_files? → run_agents → collect
    │       plan: map ReadAgent tasks to enabled specialized agents
    │       fetch_files: GitHub REST read paths for active agents (if GitHub configured)
    │       run_agents: sequential agent.process() + rate-limit sleep between agents
    │       collect: merge file changes by path
    │
    └─► GitHubController (if token + repo + not dry-run)
            create_branch → commit_files → create_pull_request
```

## Python packages

| Path | Responsibility |
|------|----------------|
| `site_sentry/config/schema.py` | `SentryConfig` and nested models (single source of truth) |
| `site_sentry/core/llm_provider.py` | `get_llm(role, config)` → LangChain chat model |
| `site_sentry/core/base_agent.py` | Abstract `BaseAgent` with LLM + `AgentMemory` |
| `site_sentry/core/memory.py` | `AgentMemory` (Chroma optional, failures are non-fatal) |
| `site_sentry/auditor/lighthouse.py` | `run_audit(url)`, `LighthouseError`, `_normalize` for tests |
| `site_sentry/agents/read_agent.py` | Lighthouse orchestration and task list for the manager |
| `site_sentry/agents/manager_agent.py` | LangGraph orchestration of five specialized agents |
| `site_sentry/agents/*_agent.py` | Specialized agents (stubs return empty `changes` until implemented) |
| `site_sentry/github/controller.py` | GitHub REST v3: refs, contents, pulls, labels |
| `site_sentry/pipeline.py` | `SentryPipeline` wiring Read → Manager → GitHub |
| `site_sentry/cli/commands.py` | Click CLI: `init`, `run`, `status` |

## LangGraph manager

- **State** (`PipelineState`): URL, scores, issues, tasks, `active_agents`, `file_contents`, `agent_results` (with reducer), `all_changes`, optional error/branch metadata.
- **Conditional edge** after `plan`: if there are no `active_agents`, skip fetch/run and go straight to `collect`.
- **Rate limiting**: `asyncio.sleep(1.5)` between consecutive specialized agent runs (approximate 40 RPM safety margin for LLM calls).

## GitHub integration

`GitHubController` expects:

- Bearer token (`GITHUB_TOKEN`)
- `repo_owner` and `repo_name` in config

File paths for the Contents API are URL-encoded per segment. PR labels are best-effort (failures are logged, not fatal).
