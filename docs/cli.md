# CLI reference

The console script is **`sentry`** (defined in `setup.py` as `site_sentry.cli.commands:cli`).

## Global options

- **`--version`**: Print package version (`1.0.0`).
- **`--help`**: Command help.

## `sentry init`

Interactive / flag-driven bootstrap.

| Option | Description |
|--------|-------------|
| `--url` | Target website URL (prompted if omitted) |
| `--workspace` | Local repo path (default: `.`) |
| `--github-owner` | GitHub org or user |
| `--github-repo` | Repository name |

Overwrites `sentry.config.yaml` only after confirmation if it already exists.

## `sentry run`

Run the full pipeline: Lighthouse → ManagerAgent → optional GitHub branch/commits/PR.

| Option | Default | Description |
|--------|---------|--------------|
| `--config` | `sentry.config.yaml` | Path to config file |
| `--url` | from config | Override audited URL |
| `--dry-run` | off | Do not create branch or PR |
| `-v` / `--verbose` | off | DEBUG logging |

If `GITHUB_TOKEN` is missing, the CLI forces **dry-run** behavior for safety.

## `sentry status`

Loads config and prints checks: config file, API key presence, GitHub token presence, `node` and `lighthouse` on `PATH`.

| Option | Default | Description |
|--------|---------|--------------|
| `--config` | `sentry.config.yaml` | Path to config file |

## Module invocation

```bash
python -m site_sentry.cli --help
```

Equivalent to the `sentry` entry point when the package is installed.
