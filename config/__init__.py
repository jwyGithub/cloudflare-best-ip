"""
配置加载：从 YAML 文件读取并解析为 Pydantic Config 模型。
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from models import Config


def load_config(path: Union[str, Path]) -> Config:
    """读取 YAML 配置文件并返回 Config 实例。"""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path.resolve()}")

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config.model_validate(raw)
