# Python module reference

High-level map of the `site_sentry` package (install with `pip install -e .`).

## `site_sentry.config`

- **`SentryConfig`**: Root settings model; use `SentryConfig.load(path)` and properties `api_key`, `github_token`.

## `site_sentry.core`

| Symbol | Module | Role |
|--------|--------|------|
| `BaseAgent` | `core.base_agent` | ABC for agents; constructs `get_llm` + `AgentMemory` |
| `get_llm`, `LLMRole` | `core.llm_provider` | Chat model factory (`"manager"` \| `"agent"`) |
| `AgentMemory` | `core.memory` | `store(data, doc_type=...)`, optional Chroma |

Convenience import:

```python
from site_sentry.core import BaseAgent, get_llm, LLMRole, AgentMemory
```

## `site_sentry.agents`

| Class | Role |
|-------|------|
| `ReadAgent` | Lighthouse audit and structured output for the manager |
| `ManagerAgent` | LangGraph orchestration (optional `GitHubController` for file fetch) |
| `SEOAgent`, `PerformanceAgent`, `ErrorFixingAgent`, `ContentUpdateAgent`, `ContentGenerationAgent` | Specialized workers; currently stubs returning `changes=[]` |

Each specialized agent: `__init__(self, config: SentryConfig)` and `async def process(self, input_data: dict) -> dict` with `status` and optional `changes`, `summary`.

## `site_sentry.auditor`

- **`run_audit(url)`** → `dict` with `scores`, `issues`, `raw_summary`
- **`LighthouseError`**: CLI / JSON failures
- **`_normalize(lhr, url)`**: Test helper for score extraction

## `site_sentry.github`

- **`GitHubController`**: REST operations (branch, file get/put, multi-file commit, PR, labels)
- **`GitHubError`**: API failures with `status_code`

## `site_sentry.pipeline`

- **`SentryPipeline`**: `async def run(url=None, dry_run=False)` — main automation entry for programs embedding Site-Sentry

## `site_sentry.cli.commands`

- **`cli`**: Root Click group (`sentry` console script target)
