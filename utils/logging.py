"""
日志系统：基于 rich 的彩色控制台日志 + 可选文件输出。
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

_console = Console(stderr=True)

# 模块级 logger，各子模块通过 get_logger(__name__) 获取
_root_logger: Optional[logging.Logger] = None


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """初始化日志系统，应在程序启动时调用一次。"""
    global _root_logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        RichHandler(
            console=_console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
    ]

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

    # 降低 httpx 和 httpcore 的日志噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _root_logger = logging.getLogger("best")
    _root_logger.setLevel(numeric_level)
    return _root_logger


def get_logger(name: str) -> logging.Logger:
    """获取命名子 logger，name 通常传 __name__。"""
    return logging.getLogger(name)
