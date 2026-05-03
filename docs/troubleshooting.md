# Troubleshooting

## `sentry run` exits before the audit

- **`NVIDIA_API_KEY`**: Must be set in `.env` for the default `nvidia_nim` provider. The CLI refuses to run without it.
- **`langchain-openai`**: Included in `install_requires`; reinstall with `pip install -e .`.

## Lighthouse failures (`LighthouseError`)

- Ensure **`node`** is on `PATH` and either **`lighthouse`** is installed globally or **`npx`** is available.
- Run `sentry status` to verify detection.
- CI sandboxes may block Chrome; use an image or runner with supported headless Chrome.

## No pull request created

- **`GITHUB_TOKEN`** missing: CLI switches to dry-run behavior.
- **`github.repo_owner` / `github.repo_name`** empty: `SentryPipeline` does not construct `GitHubController`; you get success with mode `no-github` and no PR.
- **`--dry-run`**: Intentionally skips branch and PR.

## `ImportError` for optional providers

If `llm.provider` is `google` or `groq`, install extras:

```bash
pip install -e ".[google]"
pip install -e ".[groq]"
```

## Windows console encoding

CLI user-visible lines avoid emoji so **`sentry status`** and **`sentry run`** work on `cp1252` consoles. If you embed Unicode elsewhere, set `PYTHONUTF8=1` or use UTF-8 terminal.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/test_pipeline.py -v
```

Failures on `SentryConfig.load`: check YAML path and that `website_url` includes a scheme (`https://`).
