"""
日志系统：基于 loguru 的彩色控制台日志 + 可选文件输出。
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from loguru import logger as _logger

from models import Config

_LEVEL_ALIASES = {
    "FATAL": "CRITICAL",
    "WARN": "WARNING",
}

# 模块级 logger，各子模块通过 get_logger(__name__) 获取
_root_logger: Optional[Any] = None


def _normalize_level(level: str) -> str:
    normalized = _LEVEL_ALIASES.get(level.upper(), level.upper())
    try:
        _logger.level(normalized)
    except ValueError:
        return "INFO"
    return normalized


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> Any:
    """初始化日志系统，应在程序启动时调用一次。"""
    global _root_logger

    log_level = _normalize_level(level)

    _logger.remove()
    _logger.configure(extra={"name": "best"})
    _logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[name]}</cyan> | <level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=False,
    )

    if log_file:
        _logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {extra[name]}: {message}",
            encoding="utf-8",
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )

    _root_logger = get_logger("best")
    return _root_logger


def get_logger(name: str) -> Any:
    """获取命名子 logger，name 通常传 __name__。"""
    return _logger.bind(name=name)


def _format_optional(value: str | None) -> str:
    return value if value else "<empty>"


def _format_scan_port(config: Config) -> str:
    ports = ",".join(str(port) for port in config.scan.ports)
    if len(config.scan.ports) == 1:
        return ports
    return f"<random:{ports}>"


def log_config_summary(logger: Any, config: Config) -> None:
    """输出脱敏后的运行配置摘要。"""
    sources = ",".join(config.scan.sources) if config.scan.sources else "<empty>"
    log_file = config.log.file or "<disabled>"
    github = config.sync.github if config.sync else None
    cloudflare = config.sync.cloudflare if config.sync else None
    lines = [
        "运行配置已加载",
        f"  scan: sources={sources} ports={_format_scan_port(config)} "
        f"concurrency={config.scan.concurrency} total={config.scan.total}",
        f"  output: path={config.output.path} limit={config.output.limit}",
        f"  schedule: cron={config.schedule.cron} timezone={config.schedule.timezone}",
        f"  log: level={config.log.level} file={log_file}",
    ]

    if github:
        lines.extend(
            [
                "  sync.github: "
                f"enabled={github.enabled} owner={_format_optional(github.owner)} "
                f"repo={_format_optional(github.repo)}",
                "  sync.github: "
                f"branch={_format_optional(github.branch)} "
                f"remote_path={_format_optional(github.remote_path)} "
                f"token={'<set>' if github.token else '<empty>'}",
            ]
        )
    else:
        lines.append("  sync.github: enabled=False token=<empty>")

    if cloudflare:
        lines.append(
            "  sync.cloudflare: "
            f"enabled={cloudflare.enabled} sub_domain={_format_optional(cloudflare.sub_domain)} "
            f"limit={cloudflare.limit} token={'<set>' if cloudflare.token else '<empty>'}"
        )
    else:
        lines.append("  sync.cloudflare: enabled=False sub_domain=@ limit=<default> token=<empty>")

    logger.info("\n".join(lines))
