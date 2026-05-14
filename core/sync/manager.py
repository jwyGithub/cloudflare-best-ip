"""
同步调度：根据配置调用已启用的平台同步器。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.sync.cloudflare import sync_ips_to_cloudflare_dns_from_config
from core.sync.github import sync_ips_to_github_from_config
from models import SyncConfig
from utils.logging import get_logger

logger = get_logger(__name__)


async def sync_ips_from_config(
    *,
    local_path: str | Path,
    config: SyncConfig | None,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    """
    根据同步配置执行所有已启用的平台同步。

    后续新增平台时，在这里读取对应配置并追加调用对应平台模块。
    """
    if not config:
        logger.info("未配置同步，跳过")
        return None

    results: dict[str, Any] = {}

    github_result = await sync_ips_to_github_from_config(
        local_path=local_path,
        config=config.github,
        timeout=timeout,
    )
    if github_result is not None:
        results["github"] = github_result

    cloudflare_result = await sync_ips_to_cloudflare_dns_from_config(
        local_path=local_path,
        config=config.cloudflare,
        timeout=timeout,
    )
    if cloudflare_result is not None:
        results["cloudflare"] = cloudflare_result

    if not results:
        return None
    return results
