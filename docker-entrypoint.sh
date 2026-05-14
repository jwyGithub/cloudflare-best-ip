#!/bin/sh
# docker-entrypoint.sh
# 从 SCHEDULE_CRON 读取 cron 表达式，写入 supercronic crontab，然后启动调度。
set -e

CRON_EXPR="${SCHEDULE_CRON:-0 6 * * *}"
SCHEDULE_TZ="${SCHEDULE_TIMEZONE:-Asia/Shanghai}"
export TZ="${TZ:-${SCHEDULE_TZ}}"

echo "[entrypoint] 使用 cron 表达式: ${CRON_EXPR}"
echo "[entrypoint] 使用调度时区: ${TZ}"

# 写入 supercronic crontab
CRONTAB_FILE="/tmp/crontab"
echo "${CRON_EXPR} cd /app && uv run python main.py" > "${CRONTAB_FILE}"

# 启动前先立即执行一次
echo "[entrypoint] 首次立即执行..."
cd /app && uv run python main.py || true

echo "[entrypoint] 启动 supercronic 调度..."
exec supercronic "${CRONTAB_FILE}"
