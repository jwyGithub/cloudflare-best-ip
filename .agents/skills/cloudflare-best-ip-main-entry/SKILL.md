---
name: cloudflare-best-ip-main-entry
description: Project-specific guidance for Cloudflare Best IP main.py orchestration. Use when changing the application entrypoint, execution order, output file generation, config summary logging, top-IP selection, geo label fallback, or post-run GitHub sync wiring.
---

# Cloudflare Best IP Main Entry

## Scope

Use this skill for changes centered on `main.py`, especially the end-to-end pipeline:

`load_config` -> `resolve_scan_cidrs` -> `process_cidr` -> `test_ips` -> `batch_geo_lookup` -> write output -> optional GitHub sync.

## Entry Files

- `main.py`: owns process startup, signal handler setup, config loading, summary logs, pipeline ordering, output formatting, and sync invocation.
- `utils/logging.py`: owns logging setup and the sanitized runtime config summary.
- `models/__init__.py`: read when changing data passed through the pipeline.
- `config/__init__.py`: read when changing config load or CIDR source resolution.
- `core/*.py`: read only the core module affected by the requested pipeline behavior.

## Pipeline Rules

- Keep `main()` async and keep `asyncio.run(main())` guarded by `if __name__ == "__main__"`.
- Call `setup_signal_handlers()` before potentially long-running scan work.
- Load config before logging setup, then call `setup_logging(level=config.log.level, log_file=config.log.file)`.
- Keep config summary logs in `utils.logging.log_config_summary`.
- Keep config summary logs secret-safe: print sync tokens only as `<set>` or `<empty>`.
- Let `resolve_scan_cidrs` raise `ValueError` for unknown sources and exit with status `1` from `main.py`.
- Sort successful `TestResult` values by `avg_time` and apply `config.output.limit` before geo lookup and writing.
- Preserve output line format: `ip:port#label`.
- Prefer geo label when lookup succeeds; keep `r.colo` fallback for failed or missing geo data.
- Keep GitHub sync after the local output file is written; catch `GitHubSyncError` and log it without deleting local output.

## Editing Guidance

- If adding a pipeline step, decide whether it belongs before latency testing, after ranking, after geo enrichment, or after local write.
- If changing output format, update `README.md`, Docker examples, and any sync assumptions that consume the generated text file.
- If adding config-controlled behavior, update `models.Config`, the relevant class in `config/config.py`, and the config summary logs together.
- If adding new external network calls, use async `httpx.AsyncClient`, timeouts from config, and clear failure logs.

## Verification

Prefer fast local checks first:

```bash
uv run python -m compileall main.py config core models utils
```

For an end-to-end smoke run, use a very small scan:

```bash
SCAN_TOTAL=2 SCAN_CONCURRENCY=1 SCAN_OUTPUT_LIMIT=2 uv run python main.py
```

The smoke run performs real network requests; skip it when network access is unavailable and report that clearly.
