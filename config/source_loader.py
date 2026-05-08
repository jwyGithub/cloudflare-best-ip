"""
内置 IP 源文件加载工具。
"""

from __future__ import annotations

from pathlib import Path


def load_source_file(path: Path) -> list[str]:
    """读取单个 source 文件，跳过空行和注释行。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def load_builtin_sources(source_dir: Path) -> dict[str, list[str]]:
    """从 source 目录加载所有内置 IP 源。"""
    return {
        path.stem: load_source_file(path)
        for path in sorted(source_dir.glob("*.txt"))
        if path.is_file()
    }
