"""
同步模块：对外暴露通用同步入口和各平台兼容入口。
"""

from __future__ import annotations

from core.sync.base import SyncError
from core.sync.cloudflare import (
    CloudflareDNSSyncError,
    sync_ips_to_cloudflare_dns,
    sync_ips_to_cloudflare_dns_from_config,
)
from core.sync.github import (
    GitHubSyncError,
    sync_ips_to_github,
    sync_ips_to_github_from_config,
)
from core.sync.manager import sync_ips_from_config

__all__ = [
    "CloudflareDNSSyncError",
    "GitHubSyncError",
    "SyncError",
    "sync_ips_from_config",
    "sync_ips_to_cloudflare_dns",
    "sync_ips_to_cloudflare_dns_from_config",
    "sync_ips_to_github",
    "sync_ips_to_github_from_config",
]
