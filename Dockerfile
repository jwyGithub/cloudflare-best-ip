# syntax=docker/dockerfile:1
FROM python:3.12-slim

# buildx 自动注入的目标架构（amd64 / arm64）
ARG TARGETARCH

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.45/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=e894b193bea75a5ee644e700c59e30eedc804cf7 \
    SUPERCRONIC=supercronic-linux-amd64

# CFData CLI 版本与安装路径
ENV CFDATA_VERSION=v1.7.8 \
    CFDATA_BIN=/usr/local/bin/cfdata

# 安装 supercronic 与 CFData CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    # supercronic（amd64）
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic \
    # CFData CLI（按目标架构下载并校验 sha256）
    && CFDATA_ARCH="${TARGETARCH:-amd64}" \
    && CFDATA_ASSET="cfdata-linux-${CFDATA_ARCH}" \
    && CFDATA_BASE="https://github.com/PoemMisty/CFData-WEB/releases/download/${CFDATA_VERSION}" \
    && curl -fsSL "${CFDATA_BASE}/${CFDATA_ASSET}" -o /usr/local/bin/cfdata \
    && curl -fsSL "${CFDATA_BASE}/${CFDATA_ASSET}.sha256" -o /tmp/cfdata.sha256 \
    && echo "$(cat /tmp/cfdata.sha256)  /usr/local/bin/cfdata" | sha256sum -c - \
    && chmod +x /usr/local/bin/cfdata \
    && rm -f /tmp/cfdata.sha256 \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONPATH=/app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY models/ ./models/
COPY utils/ ./utils/

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

VOLUME ["/app/output"]

ENTRYPOINT ["docker-entrypoint.sh"]
