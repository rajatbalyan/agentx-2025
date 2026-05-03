# Configuration

## Files

| File | Role |
|------|------|
| `sentry.config.yaml` | Main application config (created by `sentry init`) |
| `.env` | Secrets and optional overrides (loaded by the CLI via `python-dotenv`) |
| `site_sentry/config/sentry.config.yaml.template` | Shipped template used by `sentry init` |

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `NVIDIA_API_KEY` | Yes (for default `nvidia_nim` provider) | LLM API key |
| `GITHUB_TOKEN` | For PR workflow | GitHub REST API |
| `TARGET_URL` | No | Overrides `website_url` when loading YAML |
| `WORKSPACE_PATH` | No | Overrides `workspace_path` when loading YAML |

Secrets are **never** read from YAML; they always come from the environment (see `SentryConfig` in `site_sentry/config/schema.py`).

## YAML structure (summary)

Top-level keys (see template for full example):

- **`website_url`** (required): Live site URL, `http://` or `https://`.
- **`workspace_path`**: Local clone path (resolved to absolute).
- **`scan_interval`**: Seconds between runs if you add scheduling later.
- **`llm`**: `provider` (`nvidia_nim` | `google` | `groq` | `openai`), `manager_model`, `agent_model`, `temperature`, `max_tokens`, `base_url` (NIM).
- **`memory`**: Chroma persistence path, `collection_prefix`, `enabled`.
- **`github`**: `repo_owner`, `repo_name`, `base_branch`, `auto_merge`, `pr_labels`, `branch_prefix`.
- **`agents`**: Booleans toggling SEO, performance, error fixing, content update, content generation.
- **`logging`**: `level`, `file`, `format`.

## Loading in code

```python
from site_sentry.config import SentryConfig

config = SentryConfig.load("sentry.config.yaml")
```

Default path helper:

```python
SentryConfig.default_config_path()  # Path("sentry.config.yaml")
```
