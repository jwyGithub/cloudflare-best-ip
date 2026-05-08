"""
日志系统：基于 loguru 的彩色控制台日志 + 可选文件输出。
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from loguru import logger as _logger

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
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
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
