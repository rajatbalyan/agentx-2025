# Getting started

## Prerequisites

- **Python 3.10+**
- **Node.js** and Lighthouse: `npm install -g lighthouse` (or use `npx`, which the auditor can invoke)
- **NVIDIA NIM** API key (default LLM backend): [build.nvidia.com](https://build.nvidia.com) — set as `NVIDIA_API_KEY` in `.env`
- **GitHub** personal access token with `repo` scope (for PRs): `GITHUB_TOKEN` in `.env`

## Install

From the repository root:

```bash
pip install -e .
```

For tests and development tools:

```bash
pip install -e ".[dev]"
```

Optional LLM backends:

```bash
pip install -e ".[google]"
pip install -e ".[groq]"
```

## Initialize configuration

```bash
sentry init
```

This creates:

- `sentry.config.yaml` in the current directory (from `site_sentry/config/sentry.config.yaml.template`)
- `logs/`, `data/memory/vectors/`, `temp/lighthouse/`
- `.env` if it does not exist (template with `NVIDIA_API_KEY` and `GITHUB_TOKEN`)

Edit `.env` and set `github.repo_owner` / `github.repo_name` in `sentry.config.yaml` if you want automated commits and PRs.

## Check status

```bash
sentry status
```

Uses `sentry.config.yaml` by default. Override with:

```bash
sentry status --config path/to/sentry.config.yaml
```

## Run the pipeline

Dry run (no branch / PR):

```bash
sentry run --dry-run
```

Full run (requires GitHub repo fields + token, unless you only want audit + agent steps without commits — see [Configuration](configuration.md)):

```bash
sentry run
```

Verbose logging:

```bash
sentry run -v
```

## Next steps

- Read [Configuration](configuration.md) for all YAML and env options.
- Read [Architecture](architecture.md) for how ReadAgent, ManagerAgent, and GitHub fit together.
