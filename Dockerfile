# syntax=docker/dockerfile:1
FROM python:3.12-slim

# supercronic 用于在容器内执行 cron 任务（比 crond 更友好，日志直接输出到 stdout）
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.45/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=e894b193bea75a5ee644e700c59e30eedc804cf7 \
    SUPERCRONIC=supercronic-linux-amd64

# 安装 supercronic
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖声明，利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码（config/ 目录不提交到 git，运行时通过 volume 挂载）
COPY main.py ./
COPY config/config.example.yaml ./config/config.example.yaml
COPY core/ ./core/
COPY models/ ./models/
COPY utils/ ./utils/

# 构建 supercronic crontab（由 entrypoint 根据配置动态生成）
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# config.yaml 通过 volume 挂载到 /app/config/config.yaml
VOLUME ["/app/config", "/app/output"]

ENTRYPOINT ["docker-entrypoint.sh"]
