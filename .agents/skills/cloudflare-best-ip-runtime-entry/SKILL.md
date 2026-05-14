---
name: cloudflare-best-ip-runtime-entry
description: Project-specific guidance for Cloudflare Best IP runtime and release files. Use when changing Dockerfile, docker-compose.yml, docker-entrypoint.sh, scheduled execution with supercronic, uv runtime setup, mounted output behavior, GHCR image publishing, or release documentation.
---

# Cloudflare Best IP Runtime Entry

## Scope

Use this skill for container runtime, scheduling, deployment, and release workflow changes.

Runtime flow:

Docker image installs Python, uv, and supercronic -> `docker-entrypoint.sh` writes a crontab from env -> runs one immediate scan -> starts scheduled scans.

## Entry Files

- `Dockerfile`: Python base image, supercronic install, uv install, dependency sync, copied app files, entrypoint.
- `docker-entrypoint.sh`: runtime env logging, cron file generation, immediate run, supercronic startup.
- `docker-compose.yml`: user-facing container env and mounted `./output:/app/output`.
- `.github/workflows/docker.yml`: image build and GHCR publishing.
- `README.md`: Docker usage, env vars, release instructions.
- `pyproject.toml`, `uv.lock`: dependency and Python runtime expectations.

## Runtime Rules

- Keep `PYTHONPATH=/app` in the image so package imports work from `/app`.
- Keep `/app/output` as the container volume and document `output/...` paths for compose users.
- Keep Docker startup behavior: log env summary, run once immediately, then start supercronic.
- Never print sync tokens such as `SYNC_GITHUB_TOKEN` or `SYNC_CLOUDFLARE_TOKEN`; show only `<set>` or `<empty>`.
- Keep schedule defaults aligned across `config/constants.py`, `docker-entrypoint.sh`, `docker-compose.yml`, and `README.md`.
- Keep dependency installs reproducible with `uv sync --frozen --no-dev --no-install-project`.
- If adding Python package files, ensure `Dockerfile` copies them into `/app`.

## Scheduling Rules

- `SCHEDULE_CRON` controls the cron expression; default is `0 6 * * *`.
- `SCHEDULE_TIMEZONE` controls the scheduling timezone; `TZ` falls back to it.
- The generated crontab should run from `/app` and call `uv run python main.py`.
- The immediate startup run may fail without stopping the container; preserve `|| true` unless the user explicitly wants strict startup failure.

## Release Rules

- Keep tag-triggered release docs aligned with `.github/workflows/docker.yml`.
- When changing image names, update README pull/run examples and compose image reference together.
- When adding env vars, update compose, entrypoint logging, README configuration table, and config parsing.

## Verification

Run shell and Python syntax checks:

```bash
sh -n docker-entrypoint.sh
uv run python -m compileall main.py config core models utils
```

When Docker is available, build locally:

```bash
docker build -t cloudflare-best-ip:local .
```

Avoid running publish workflows locally unless the user explicitly asks for release or registry work.
