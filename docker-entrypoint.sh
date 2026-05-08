#!/bin/sh
# docker-entrypoint.sh
# 从 SCHEDULE_CRON 读取 cron 表达式，写入 supercronic crontab，然后启动调度。
set -e

CRON_EXPR="${SCHEDULE_CRON:-0 0 * * *}"

echo "[entrypoint] 使用 cron 表达式: ${CRON_EXPR}"
echo "[entrypoint] SCAN_SOURCE=${SCAN_SOURCE:-<default>} SCAN_PORT=${SCAN_PORT:-<random>}"
echo "[entrypoint] SCAN_CONCURRENCY=${SCAN_CONCURRENCY:-<default>} SCAN_TOTAL=${SCAN_TOTAL:-<default>} SCAN_OUTPUT_PATH=${SCAN_OUTPUT_PATH:-<default>} SCAN_OUTPUT_LIMIT=${SCAN_OUTPUT_LIMIT:-<default>}"
echo "[entrypoint] SCHEDULE_CRON=${SCHEDULE_CRON:-<default>} SCHEDULE_TIMEZONE=${SCHEDULE_TIMEZONE:-<default>} LOG_LEVEL=${LOG_LEVEL:-<default>}"
echo "[entrypoint] SYNC_GITHUB_OWNER=${SYNC_GITHUB_OWNER:-<empty>} SYNC_GITHUB_REPO=${SYNC_GITHUB_REPO:-<empty>} SYNC_GITHUB_BRANCH=${SYNC_GITHUB_BRANCH:-<empty>} SYNC_GITHUB_REMOTE_PATH=${SYNC_GITHUB_REMOTE_PATH:-<empty>}"
if [ -n "${SYNC_GITHUB_TOKEN}" ]; then
    echo "[entrypoint] SYNC_GITHUB_TOKEN=<set>"
else
    echo "[entrypoint] SYNC_GITHUB_TOKEN=<empty>"
fi

# 写入 supercronic crontab
CRONTAB_FILE="/tmp/crontab"
echo "${CRON_EXPR} cd /app && uv run python main.py" > "${CRONTAB_FILE}"

# 启动前先立即执行一次
echo "[entrypoint] 首次立即执行..."
cd /app && uv run python main.py || true

echo "[entrypoint] 启动 supercronic 调度..."
exec supercronic "${CRONTAB_FILE}"
