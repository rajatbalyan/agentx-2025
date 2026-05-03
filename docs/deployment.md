# Deployment

## Docker image

The root [Dockerfile](../Dockerfile) defines a **Python 3.11** image with **Node.js 20** and **Lighthouse** globally installed, then:

1. `pip install -r requirements.txt`
2. `pip install -e .` for the `site_sentry` package
3. **`ENTRYPOINT ["sentry"]`** and **`CMD ["run"]`** so the default container command is `sentry run`

Build:

```bash
docker build -t site-sentry:local .
```

Run (mount your project so `sentry.config.yaml` and `.env` exist under `/app`):

```bash
docker run --rm -it -v "%cd%":/app -w /app site-sentry:local
```

Override command:

```bash
docker run --rm -it -v "%cd%":/app -w /app site-sentry:local status
```

(On Unix, replace `%cd%` with `"$(pwd)"`.)

## Docker Compose

[docker-compose.yml](../docker-compose.yml) defines a single service **`site-sentry`**:

- Builds from the repository root
- Loads environment from **`.env`**
- Binds the current directory to **`/app`**
- Sets **`working_dir: /app`**
- Runs **`command: ["run"]`** so the effective process is `sentry run`

Start:

```bash
docker compose run --rm site-sentry
```

Ensure `sentry.config.yaml` and `.env` are present in the mounted directory before expecting a successful pipeline.

## Production notes

- Lighthouse needs a headless-capable environment (Chromium is not installed in the slim image by default; the CLI uses Lighthouse’s headless Chrome flags). If audits fail in minimal containers, use a richer base image or install Chromium dependencies.
- Store secrets via orchestrator secrets (Kubernetes secrets, ECS task definitions, etc.), not in the image.
- Rate limits (NIM ~40 RPM) are partially addressed by sequential agent execution and sleeps in `ManagerAgent`; tune as needed.
