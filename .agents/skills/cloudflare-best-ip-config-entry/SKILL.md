---
name: cloudflare-best-ip-config-entry
description: Project-specific guidance for Cloudflare Best IP configuration modules. Use when changing environment variable parsing, class-based config defaults, Pydantic config models, built-in source files, SCAN_SOURCE or SCAN_PORT behavior, or README configuration documentation.
---

# Cloudflare Best IP Config Entry

## Scope

Use this skill for changes centered on the configuration package and config model contract.

The config flow is:

`EnvConfig.from_os()` -> `AppConfig().resolve(env)` -> `models.Config` -> `config/__init__.py` source resolution.

## Entry Files

- `config/config.py`: class-based default values, `EnvConfig`, `AppConfig`, environment parsing, and runtime `models.Config` resolution.
- `config/constants.py`: compatibility exports for built-in source loading only; do not add runtime defaults here.
- `config/__init__.py`: public config API, especially `load_config()` and `resolve_scan_cidrs()`.
- `config/source/*.txt`: built-in CIDR source names; file stem is the source name.
- `models/__init__.py`: Pydantic models that must match config data.
- `README.md`, `docker-compose.yml`, `docker-entrypoint.sh`: update when user-facing env vars change.

## Config Rules

- Keep `SCAN_SOURCE` environment-only and map it to `config.scan.sources`.
- Treat blank environment values as unset via `_env_value`.
- Parse positive integer env vars with `_parse_positive_int`; raise `ValueError` for invalid positive-int fields.
- Keep `SCAN_PORT` forgiving: ignore invalid port tokens and fall back to the default random port pool when no valid port remains.
- Keep valid port range as `1..65535`.
- Enable GitHub sync only when owner, repo, branch, remote path, and token are all present.
- Enable Cloudflare DNS sync when token is present; `sub_domain` defaults to `@` and may be overridden by `SYNC_CLOUDFLARE_SUB_DOMAIN`.
- Keep Cloudflare DNS `limit` positive; it defaults to `10` and may be overridden by `SYNC_CLOUDFLARE_LIMIT`.
- Do not log raw tokens in config summaries or runtime scripts.
- Keep defaults in the closest domain config class in `config/config.py`; `AppConfig` should compose classes, not duplicate defaults.
- Keep `AppConfig.resolve(...)` output aligned with `models.Config`; add model fields and config defaults together.

## Built-In Sources

- Add a source by creating `config/source/<name>.txt`.
- Use CIDR lines only; blank lines and lines starting with `#` are ignored.
- Keep source names lowercase and simple because users pass them through `SCAN_SOURCE`.
- When changing source resolution errors, preserve the available-source list so users can fix typos.

## Editing Guidance

- For a new env var, update `EnvConfig`, the relevant domain config class in `config/config.py`, `models/__init__.py` when the runtime shape changes, and `README.md`.
- If Docker users need the env var, also update `docker-compose.yml` and `docker-entrypoint.sh`.
- Avoid hidden config aliases unless there is a compatibility requirement; document any alias in `README.md`.
- Prefer Pydantic validation for structural config shape and small `EnvConfig` parser helpers for env string conversion.

## Verification

Run syntax and config import checks:

```bash
uv run python -m compileall config models
uv run python -c "from config import load_config, resolve_scan_cidrs; c=load_config(); print(c.scan.sources); print(len(resolve_scan_cidrs(c)))"
```

Check selected env behavior with small one-off commands:

```bash
SCAN_PORT=443,8443 SCAN_SOURCE=cloudflare uv run python -c "from config import load_config; print(load_config().scan.ports)"
```
