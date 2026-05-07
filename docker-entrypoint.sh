#!/bin/sh
# docker-entrypoint.sh
# 从 config.yaml 读取 cron 表达式，写入 supercronic crontab，然后启动调度。
# 若 CONFIG_YAML 环境变量有值，则将其内容写入 /app/config/config.yaml（适合 k8s Secret / Docker secret）。
set -e

CONFIG_PATH="/app/config/config.yaml"

# 支持通过环境变量直接注入配置内容（base64 编码）
if [ -n "${CONFIG_YAML_BASE64}" ]; then
    echo "[entrypoint] 从 CONFIG_YAML_BASE64 写入配置..."
    mkdir -p /app/config
    echo "${CONFIG_YAML_BASE64}" | base64 -d > "${CONFIG_PATH}"
fi

# 配置文件不存在时，使用示例配置并警告
if [ ! -f "${CONFIG_PATH}" ]; then
    echo "[entrypoint] 警告: 未找到 ${CONFIG_PATH}，使用示例配置（仅供测试）"
    cp /app/config/config.example.yaml "${CONFIG_PATH}"
fi

# 解析 cron 表达式（取 schedule.cron 字段，默认 "0 0 * * *"）
CRON_EXPR=$(python3 -c "
import yaml, sys
try:
    with open('${CONFIG_PATH}') as f:
        cfg = yaml.safe_load(f)
    print(cfg.get('schedule', {}).get('cron', '0 0 * * *'))
except Exception as e:
    print('0 0 * * *', file=sys.stderr)
    print('0 0 * * *')
")

echo "[entrypoint] 使用 cron 表达式: ${CRON_EXPR}"

# 写入 supercronic crontab
CRONTAB_FILE="/tmp/crontab"
echo "${CRON_EXPR} cd /app && uv run python main.py" > "${CRONTAB_FILE}"

# 启动前先立即执行一次
echo "[entrypoint] 首次立即执行..."
cd /app && uv run python main.py || true

echo "[entrypoint] 启动 supercronic 调度..."
exec supercronic "${CRONTAB_FILE}"
