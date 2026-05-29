"""
配置兼容导出。

默认值已迁移到 config.config 中的领域配置类；这里仅保留内置源相关常量。
"""

from __future__ import annotations

from pathlib import Path

from config.source_loader import load_builtin_sources


SOURCE_DIR = Path(__file__).parent / "source"
BUILTIN_SOURCES: dict[str, list[str]] = load_builtin_sources(SOURCE_DIR)
