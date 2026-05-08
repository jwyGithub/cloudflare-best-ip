"""
配置解析工具：从默认配置和环境变量生成运行配置。
"""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Any


def _env_value(name: str) -> str | None:
    """读取环境变量，未设置或空白时返回 None。"""
    raw = os.getenv(name)
    if raw is None:
        return None

    value = raw.strip()
    return value or None


def _parse_positive_int(name: str) -> int | None:
    """从环境变量读取正整数。"""
    value = _env_value(name)
    if value is None:
        return None

    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 环境变量必须是正整数: {value}") from exc

    if number <= 0:
        raise ValueError(f"{name} 环境变量必须大于 0: {number}")
    return number


def parse_env_sources() -> list[str] | None:
    """从 SCAN_SOURCE 环境变量读取源名称，支持逗号分隔。"""
    value = _env_value("SCAN_SOURCE")
    if value is None:
        return None

    sources = [item.strip() for item in value.split(",") if item.strip()]
    return sources or None


def parse_env_ports() -> list[int] | None:
    """从 SCAN_PORT 环境变量读取合法端口，支持逗号分隔。"""
    value = _env_value("SCAN_PORT")
    if value is None:
        return None

    values = [item.strip() for item in value.split(",") if item.strip()]
    if not values:
        return None

    ports: list[int] = []
    for value in values:
        try:
            port = int(value)
        except ValueError:
            continue

        if 1 <= port <= 65535:
            ports.append(port)

    return ports or None


def apply_env_overrides(config: dict[str, Any]) -> None:
    """把环境变量覆盖到已合并的配置上。"""
    env_sources = parse_env_sources()
    if env_sources is not None:
        config["scan"]["sources"] = env_sources

    env_ports = parse_env_ports()
    if env_ports is not None:
        config["scan"]["ports"] = env_ports

    scan_concurrency = _parse_positive_int("SCAN_CONCURRENCY")
    if scan_concurrency is not None:
        config["scan"]["concurrency"] = scan_concurrency

    scan_total = _parse_positive_int("SCAN_TOTAL")
    if scan_total is not None:
        config["scan"]["total"] = scan_total

    output_path = _env_value("SCAN_OUTPUT_PATH")
    if output_path is not None:
        config["output"]["path"] = output_path

    output_limit = _parse_positive_int("SCAN_OUTPUT_LIMIT")
    if output_limit is not None:
        config["output"]["limit"] = output_limit

    schedule_cron = _env_value("SCHEDULE_CRON")
    if schedule_cron is not None:
        config["schedule"]["cron"] = schedule_cron

    schedule_timezone = _env_value("SCHEDULE_TIMEZONE")
    if schedule_timezone is not None:
        config["schedule"]["timezone"] = schedule_timezone

    log_level = _env_value("LOG_LEVEL")
    if log_level is not None:
        config["log"]["level"] = log_level

    sync_github = config.setdefault("sync", {}).setdefault("github", {})
    sync_owner = _env_value("SYNC_GITHUB_OWNER")
    if sync_owner is not None:
        sync_github["owner"] = sync_owner

    sync_repo = _env_value("SYNC_GITHUB_REPO")
    if sync_repo is not None:
        sync_github["repo"] = sync_repo

    sync_branch = _env_value("SYNC_GITHUB_BRANCH")
    if sync_branch is not None:
        sync_github["branch"] = sync_branch

    sync_remote_path = _env_value("SYNC_GITHUB_REMOTE_PATH")
    if sync_remote_path is not None:
        sync_github["remote_path"] = sync_remote_path

    sync_token = _env_value("SYNC_GITHUB_TOKEN")
    if sync_token is not None:
        sync_github["token"] = sync_token

    required_sync_values = [
        sync_github.get("owner"),
        sync_github.get("repo"),
        sync_github.get("branch"),
        sync_github.get("remote_path"),
        sync_github.get("token"),
    ]
    if all(required_sync_values):
        sync_github["enabled"] = True


def build_config_data(default: dict[str, Any]) -> dict[str, Any]:
    """根据默认配置和环境变量生成配置数据。"""
    merged = deepcopy(default)
    apply_env_overrides(merged)
    return merged
