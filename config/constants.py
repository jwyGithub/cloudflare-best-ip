"""
默认配置常量。

未通过环境变量覆盖配置项时，会使用这里的默认值。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config.source_loader import load_builtin_sources


ports = [443, 2053, 2083, 2087, 2096, 8443]
SOURCE_DIR = Path(__file__).parent / "source"

BUILTIN_SOURCES: dict[str, list[str]] = load_builtin_sources(SOURCE_DIR)

DEFAULT_CONFIG: dict[str, Any] = {
    "scan": {
        "sources": ["cloudflare"],
        "ports": ports,
        "concurrency": 8,
        "total": 512,
        "test_url": "https://{hex_ip}.nip.lfree.org:{port}/cdn-cgi/trace",
    },
    "output": {
        "path": "output/ips.txt",
        "limit": 60,
    },
    "log": {
        "level": "INFO",
        "file": None,
    },
    "http": {
        "timeout": 5,
        "retries": 3,
        "retry_delay": 1.0,
    },
    "geo": {
        "url": "http://ip-api.com/batch",
        "batch_limit": 100,
        "fields": "status,countryCode,region,query",
        "timeout": 10.0,
        "retries": 3,
        "retry_delay": 1.0,
    },
    "schedule": {
        "cron": "0 6 * * *",
        "timezone": "Asia/Shanghai",
    },
    "sync": {
        "github": {
            "enabled": False,
            "owner": None,
            "repo": None,
            "remote_path": "ips.txt",
            "branch": "main",
            "token": None,
            "commit_message": f"chore: update ips.txt on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
    },
}
