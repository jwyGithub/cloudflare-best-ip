# cloudflare-best-ip

[![Build & Publish Docker Image](https://github.com/jwyGithub/cloudflare-best-ip/actions/workflows/docker.yml/badge.svg)](https://github.com/jwyGithub/cloudflare-best-ip/actions/workflows/docker.yml)

A Python tool that samples IPs from Cloudflare CIDR lists, tests latency via `cdn-cgi/trace`, enriches results with geo info, and writes the best IPs to a plain-text file — scheduled automatically via Docker + supercronic.

## Features

- Samples IPs from built-in CIDR sources
- Concurrent latency testing with `asyncio` (concurrency controlled by `scan.concurrency`)
- Geo lookup via [ip-api.com](http://ip-api.com) batch API
- Output format: `ip:port#CountryCode-Region` (e.g. `1.2.3.4:443#CN-Guangdong`)
- Scheduled execution using supercronic inside Docker
- Configuration via environment variables
- Optional GitHub sync via the GitHub Contents API
- Optional Cloudflare DNS sync for A records

## Quick Start

```bash
docker compose up -d
```

To run locally with [uv](https://github.com/astral-sh/uv):

```bash
uv run python main.py
```

## Configuration

Defaults are defined in `config/constants.py`. Override values with environment variables.
`SCAN_SOURCE` is only read from the environment. Source names come from `config/source/*.txt`; if unset or empty, `cloudflare` is used.
By default, the port is randomly selected from `443,2053,2083,2087,2096,8443`. Set `SCAN_PORT=443` to force a fixed port at runtime. If `SCAN_PORT` is empty or invalid, the default random port pool is used.

| Section    | Description                                    |
| ---------- | ---------------------------------------------- |
| `scan`     | Ports, concurrency, sample size                          |
| `schedule` | Cron expression and timezone for Docker scheduling |
| `output`   | Output file path and max number of IPs to keep. Use `output/...` with Docker Compose so files land in the mounted `./output` directory |
| `http`     | Request timeout and retries                    |
| `geo`      | ip-api.com batch query settings                |
| `log`      | Log level and optional log file path           |
| `sync`     | Optional GitHub and Cloudflare DNS sync settings |

Default schedule: `0 6 * * *` in `Asia/Shanghai` timezone.

Environment overrides:

| Variable             | Description                         |
| -------------------- | ----------------------------------- |
| `SCAN_SOURCE`        | Built-in source name from `config/source/*.txt`, e.g. `cloudflare` |
| `SCAN_PORT`          | Fixed port; unset or invalid means random port |
| `SCAN_CONCURRENCY`   | Number of concurrent latency test coroutines |
| `SCAN_TOTAL`         | Number of sampled IPs               |
| `SCAN_OUTPUT_PATH`   | Output file path                    |
| `SCAN_OUTPUT_LIMIT`  | Max number of IPs to keep           |
| `SCHEDULE_CRON`      | Cron expression                     |
| `SCHEDULE_TIMEZONE`  | IANA timezone name                  |
| `LOG_LEVEL`          | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SYNC_GITHUB_OWNER`  | GitHub user or organization         |
| `SYNC_GITHUB_REPO`   | GitHub repository name              |
| `SYNC_GITHUB_BRANCH` | Branch to update                    |
| `SYNC_GITHUB_REMOTE_PATH` | Target file path in repository |
| `SYNC_GITHUB_TOKEN`  | GitHub token                        |
| `SYNC_CLOUDFLARE_SUB_DOMAIN` | DNS record name to update. Defaults to `@` for the zone apex |
| `SYNC_CLOUDFLARE_LIMIT` | Max number of unique IPs to sync to Cloudflare DNS. Defaults to `10` |
| `SYNC_CLOUDFLARE_TOKEN` | Cloudflare API token with Zone/DNS edit permissions |

### GitHub Sync

GitHub sync is disabled unless all required GitHub sync environment variables are set:

```bash
SYNC_GITHUB_OWNER=your-github-name
SYNC_GITHUB_REPO=your-repo
SYNC_GITHUB_BRANCH=main
SYNC_GITHUB_REMOTE_PATH=ips.txt
SYNC_GITHUB_TOKEN=github_pat_xxx
```

When all five values are set, GitHub sync is enabled automatically.

### Cloudflare DNS Sync

Cloudflare DNS sync updates A records for the first zone returned by the Cloudflare API token.
It deletes existing A records for the target record name, then creates one A record for each unique IP in the output file.

```bash
SYNC_CLOUDFLARE_TOKEN=your-cloudflare-api-token
```

When `SYNC_CLOUDFLARE_TOKEN` is set, Cloudflare DNS sync is enabled automatically.
`SYNC_CLOUDFLARE_SUB_DOMAIN` is optional and defaults to `@`.
`SYNC_CLOUDFLARE_LIMIT` is optional and defaults to `10`.

## Docker

Pull the latest image:

```bash
docker pull ghcr.io/jwygithub/cloudflare-best-ip:latest
```

Run with environment overrides:

```bash
docker run \
  -e SCAN_SOURCE="cloudflare" \
  -e SCAN_PORT="443" \
  -e SCAN_CONCURRENCY="8" \
  -e SCAN_TOTAL="30" \
  -e SCAN_OUTPUT_PATH="output/result.txt" \
  -e SCAN_OUTPUT_LIMIT="30" \
  -e SCHEDULE_CRON="0 6 * * *" \
  -e SCHEDULE_TIMEZONE="Asia/Shanghai" \
  -e LOG_LEVEL="INFO" \
  -e SYNC_GITHUB_OWNER="your-github-name" \
  -e SYNC_GITHUB_REPO="your-repo" \
  -e SYNC_GITHUB_BRANCH="main" \
  -e SYNC_GITHUB_REMOTE_PATH="ips.txt" \
  -e SYNC_GITHUB_TOKEN="github_pat_xxx" \
  -e SYNC_CLOUDFLARE_LIMIT="10" \
  -e SYNC_CLOUDFLARE_TOKEN="cloudflare_api_token_xxx" \
  -v ./output:/app/output \
  ghcr.io/jwygithub/cloudflare-best-ip:latest
```

Omit `SCAN_PORT` to randomly select from the built-in port pool.

## Publishing a Release

Push a tag matching `v*` to trigger the build workflow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds multi-arch images (`amd64` + `arm64`) and pushes them to GHCR.

## License

ISC
