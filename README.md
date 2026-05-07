# cloudflare-best-ip

[![Build & Publish Docker Image](https://github.com/jwyGithub/cloudflare-best-ip/actions/workflows/docker.yml/badge.svg)](https://github.com/jwyGithub/cloudflare-best-ip/actions/workflows/docker.yml)

A Python tool that samples IPs from Cloudflare CIDR lists, tests latency via `cdn-cgi/trace`, enriches results with geo info, and writes the best IPs to a plain-text file — scheduled automatically via Docker + supercronic.

## Features

- Fetches and samples IPs from configurable CIDR sources
- Concurrent latency testing with `asyncio` (concurrency controlled by `scan.thread`)
- Geo lookup via [ip-api.com](http://ip-api.com) batch API
- Output format: `ip:port#CountryCode-Region` (e.g. `1.2.3.4:443#CN-Guangdong`)
- Scheduled execution using supercronic inside Docker (cron expression from `config.yaml`)
- Config injected via volume mount or `CONFIG_YAML_BASE64` environment variable

## Quick Start

```bash
# 1. Copy and edit config
cp config.example.yaml config.yaml

# 2. Run with Docker Compose
docker compose up -d
```

To run locally with [uv](https://github.com/astral-sh/uv):

```bash
uv run python main.py
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and adjust as needed. Key sections:

| Section    | Description                                    |
| ---------- | ---------------------------------------------- |
| `scan`     | IP sources, ports, concurrency, sample size    |
| `schedule` | Cron expression (UTC) and timezone for logging |
| `output`   | Output file path and max number of IPs to keep |
| `http`     | Request timeout, retries for CIDR fetching     |
| `geo`      | ip-api.com batch query settings                |
| `log`      | Log level and optional log file path           |

Default schedule: `0 0 * * *` (UTC 00:00 = UTC+8 08:00).

## Docker

Pull the latest image:

```bash
docker pull ghcr.io/jwygithub/cloudflare-best-ip:latest
```

Inject config without a volume (base64-encoded):

```bash
docker run \
  -e CONFIG_YAML_BASE64="$(base64 -i config.yaml)" \
  -v ./output:/app/output \
  ghcr.io/jwygithub/cloudflare-best-ip:latest
```

## Publishing a Release

Push a tag matching `v*` to trigger the build workflow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds multi-arch images (`amd64` + `arm64`) and pushes them to GHCR.

## License

ISC
