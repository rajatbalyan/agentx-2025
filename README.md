# Site-Sentry

Autonomous website maintenance agent: **Lighthouse audit → LLM fixes → GitHub PR**.

## What It Does

- **Audits** your live site with Lighthouse (performance, SEO, accessibility, best practices) and turns results into prioritized tasks.
- **Plans and applies fixes** through a LangGraph `ManagerAgent` and specialized agents (SEO, performance, error fixing, optional content update/generation).
- **Opens a pull request** on GitHub with proposed file changes when credentials are configured (or reports results in dry-run / no-GitHub modes).

## Quick Start

```bash
pip install -e ".[dev]"
```

```bash
sentry init
```

Edit `.env` with `NVIDIA_API_KEY` and `GITHUB_TOKEN`, then:

```bash
sentry run
```

Preview without committing:

```bash
sentry run --dry-run
```

## Prerequisites

- **Python 3.10+**
- **Node.js** and Lighthouse: `npm install -g lighthouse` (or use `npx`)
- **NVIDIA NIM** API key (free tier): [build.nvidia.com](https://build.nvidia.com)
- **GitHub** Personal Access Token with `repo` (or `public_repo` for public repos only)

## Configuration

- **`sentry.config.yaml`** (create with `sentry init` from the bundled template): `website_url`, `workspace_path`, `scan_interval`, `llm`, `memory`, `github`, `agents`, `logging`.
- **Secrets** are read only from the environment (`NVIDIA_API_KEY`, `GITHUB_TOKEN`), not from YAML.
- Optional overrides: `TARGET_URL`, `WORKSPACE_PATH` env vars when loading config.

## LLM Provider

- Default provider is **NVIDIA NIM** (OpenAI-compatible API, free tier, ~40 RPM). Models for manager vs agents are set under `llm.manager_model` and `llm.agent_model`.
- Optional extras: `pip install -e ".[google]"` or `pip install -e ".[groq]"` and set `llm.provider` in config (`google` / `groq`). Key selection follows `site_sentry.core.llm_provider` and `SentryConfig`.

## Architecture

```text
ReadAgent (Lighthouse) → ManagerAgent (LangGraph)
                              ↓
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    SEOAgent   PerformanceAgent   ErrorFixingAgent
        │               │               │
        └───────────────┴───────────────┘
                              ↓
              ContentUpdate / ContentGeneration (optional toggles)
                              ↓
                   GitHubController (branch, commits, PR)
```

## CLI

| Command | Purpose |
|--------|---------|
| `sentry init` | Create `sentry.config.yaml`, dirs, `.env` template |
| `sentry run` | Full pipeline |
| `sentry status` | Config and tool checks |

## Documentation

Full guides (install, config, CLI, architecture, deployment, troubleshooting): **[docs/README.md](docs/README.md)**

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/test_pipeline.py -v
```
