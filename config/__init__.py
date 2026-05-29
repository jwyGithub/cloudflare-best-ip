"""
配置加载：从类化配置和环境变量解析为 Pydantic Config 模型。
"""

from __future__ import annotations

from config.config import AppConfig, EnvConfig
from models import Config


def load_config() -> Config:
    """从默认配置和环境变量返回 Config 实例。"""
    return AppConfig().resolve(EnvConfig.from_os())


def resolve_scan_cidrs(config: Config) -> list[str]:
    """根据配置中的源名称解析内置 CIDR 列表。"""
    builtin_sources = AppConfig().source.sources
    cidrs: list[str] = []
    for source in config.scan.sources:
        source_cidrs = builtin_sources.get(source)
        if source_cidrs is None:
            available = ", ".join(sorted(builtin_sources))
            raise ValueError(f"未知 IP 源: {source}，可用源: {available}")
        cidrs.extend(source_cidrs)
    return cidrs
