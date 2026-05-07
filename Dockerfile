# syntax=docker/dockerfile:1
FROM python:3.12-slim

# supercronic 用于在容器内执行 cron 任务（比 crond 更友好，日志直接输出到 stdout）
ENV SUPERCRONIC_VERSION=0.2.33 \
    SUPERCRONIC_SHA1=59353d7b4a6fa12e9e8df33c6eb6dd71a31cb1b4

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
       -o /usr/local/bin/supercronic \
    && echo "${SUPERCRONIC_SHA1}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic \
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
