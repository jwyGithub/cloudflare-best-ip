---
name: cloudflare-best-ip-core-entry
description: Project-specific guidance for Cloudflare Best IP core modules. Use when changing CIDR sampling, random port selection, Cloudflare /ip.json latency testing, geo lookup, async concurrency, retry behavior, TestResult data, GitHub Contents API sync, or Cloudflare DNS sync logic.
---

# Cloudflare Best IP Core Entry

## Scope

Use this skill for changes centered on scanning, testing, enrichment, and publishing internals.

Core flow:

`core/cidr.py` samples `ip:port` entries -> `core/test.py` tests Cloudflare `/ip.json` latency -> `core/geo.py` enriches winning IPs -> `core/sync/` optionally publishes output.

## Entry Files

- `core/cidr.py`: CIDR sampling, uniqueness, random port application.
- `core/test.py`: async latency test, `/ip.json` parsing, `TestResult` creation.
- `core/geo.py`: ip-api.com batch requests and label generation.
- `core/sync/__init__.py`: public sync exports used by `main.py`.
- `core/sync/base.py`: shared sync error types.
- `core/sync/manager.py`: dispatch configured sync platforms.
- `core/sync/github.py`: GitHub Contents API upload/update.
- `core/sync/cloudflare.py`: Cloudflare DNS A-record delete/create sync.
- `utils/__init__.py`: CIDR IP generation, port selection, IPv4 hex conversion.
- `utils/logging.py`: use existing logger pattern for core logs.
- `models/__init__.py`: shared `Config`, `TestResult`, and sync/geo config models.

## Core Contracts

- `process_cidr` returns unique strings in `ip:port` form.
- CIDR sampling currently supports IPv4 via `ipaddress.IPv4Network`; expand models and test URL behavior before adding IPv6.
- `test_ips` accepts `list[str]` entries in `ip:port` or `ip:port#remark` form and returns `list[TestResult]`.
- `_test_single_ip` matches `index.html` `testLatency`: build one cache-busted `/ip.json` URL, run OPTIONS preflight up to 3 times with `timeout * 2`, then time one successful GET including JSON parsing.
- `config.scan.test_url` must support `{hex_ip}` and `{port}` placeholders and default to `https://{hex_ip}.nip.cmliussss.hidns.vip:{port}/ip.json`.
- `utils.ip_to_hex` returns the uppercase IPv4 hex label used by the JS probe URL.
- `batch_geo_lookup` returns `dict[ip, GeoInfo]` and must tolerate failed batches by returning fail entries.
- `GeoInfo.label` should stay compatible with `main.py` output labels.
- `sync_ips_from_config` must dispatch enabled platform sync modules and raise `SyncError` subclasses for platform failures.
- `sync_ips_to_github` must require a token, handle create vs update via remote sha, and raise `GitHubSyncError` for API failures.
- `sync_ips_to_cloudflare_dns` must derive zone ID/domain from the token, delete existing A records for `sub_domain`, and recreate up to `limit` unique records from the output file IPs.

## Async And Network Rules

- Reuse `httpx.AsyncClient` for repeated calls.
- Keep concurrency bounded with `asyncio.Semaphore` in latency testing.
- Keep timeout, retry, and retry delay values config-driven.
- Keep the JS-aligned latency semantics: OPTIONS failures reject the IP; only the single GET timing becomes `TestResult.avg_time`.
- Log per-IP successes at info level only where already established; keep noisy failures at debug unless they are final batch failures.
- Do not swallow platform API errors inside `core/sync/`; raise `SyncError` subclasses and let `main.py` decide whether to continue.

## Editing Guidance

- If changing `TestResult`, update `main.py` output handling and any sort/filter logic.
- If changing `/ip.json` parsing, keep field access tolerant of unknown or missing Cloudflare fields.
- If changing geo fields, update the relevant config class in `config/config.py` and `GeoInfo`.
- If adding a new publisher, create a new `core/sync/<platform>.py` module, add config fields in `models.SyncConfig`, and dispatch it from `core/sync/manager.py`.
- If randomness becomes test-sensitive, inject or seed randomness at the smallest practical boundary.

## Verification

Run local syntax checks:

```bash
uv run python -m compileall core utils models
```

Run focused parser checks without network:

```bash
uv run python -c "from utils import ip_to_hex; print(ip_to_hex('1.2.3.4'))"
uv run python -m unittest tests.test_latency_logic tests.test_config_loading
```

For network smoke testing, keep sample size small:

```bash
SCAN_TOTAL=2 SCAN_CONCURRENCY=1 SCAN_OUTPUT_LIMIT=2 uv run python main.py
```
