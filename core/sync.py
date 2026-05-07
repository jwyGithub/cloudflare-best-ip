"""
GitHub 同步：将本地 ips.txt 同步到指定 GitHub 仓库文件。
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from models import GitHubSyncConfig

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubSyncError(RuntimeError):
    """GitHub 同步失败。"""


async def sync_ips_to_github(
    *,
    local_path: str | Path = "output/ips.txt",
    owner: str,
    repo: str,
    remote_path: str = "ips.txt",
    token: str | None = None,
    branch: str = "main",
    commit_message: str = "chore: update ips.txt",
    timeout: float = 20.0,
) -> dict[str, Any]:
    """
    将本地 IP 文件同步到 GitHub 仓库。

    使用 GitHub Contents API：
    - 远端文件存在时，带 sha 更新文件
    - 远端文件不存在时，创建新文件

    Args:
        local_path: 本地 ips.txt 路径。
        owner: GitHub 仓库 owner，例如 "octocat"。
        repo: GitHub 仓库名。
        remote_path: 仓库内目标文件路径。
        token: GitHub token；为空时读取 GITHUB_TOKEN 环境变量。
        branch: 目标分支。
        commit_message: 提交信息。
        timeout: GitHub API 请求超时时间。

    Returns:
        GitHub API 返回的 JSON。
    """
    github_token = token or os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise GitHubSyncError("缺少 GitHub token，请传入 token 或设置 GITHUB_TOKEN 环境变量")

    source = Path(local_path)
    if not source.exists():
        raise GitHubSyncError(f"本地文件不存在: {source.resolve()}")
    if not source.is_file():
        raise GitHubSyncError(f"本地路径不是文件: {source.resolve()}")

    content = source.read_bytes()
    encoded_content = base64.b64encode(content).decode("ascii")
    api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{remote_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        sha = await _get_remote_sha(client, api_url, headers, branch)
        payload: dict[str, Any] = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        action = "更新" if sha else "创建"
        logger.info("开始同步 GitHub 文件: %s/%s:%s (%s)", owner, repo, remote_path, action)
        response = await client.put(api_url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise GitHubSyncError(
                f"GitHub 文件同步失败: HTTP {response.status_code} - {response.text}"
            )

    logger.info("GitHub 文件同步完成: %s/%s:%s", owner, repo, remote_path)
    return response.json()


async def sync_ips_to_github_from_config(
    *,
    local_path: str | Path,
    config: GitHubSyncConfig | None,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    """
    根据配置同步 IP 文件。

    配置不存在、未启用、或 owner/repo 缺失时返回 None，不执行同步。
    """
    if not config:
        logger.info("未配置 GitHub 同步，跳过")
        return None
    if not config.enabled:
        logger.info("GitHub 同步未启用，跳过")
        return None
    if not config.owner or not config.repo:
        logger.warning("GitHub 同步缺少 owner 或 repo，跳过")
        return None

    token = config.token or os.getenv(config.token_env)
    return await sync_ips_to_github(
        local_path=local_path,
        owner=config.owner,
        repo=config.repo,
        remote_path=config.remote_path,
        token=token,
        branch=config.branch,
        commit_message=config.commit_message,
        timeout=timeout,
    )


async def _get_remote_sha(
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict[str, str],
    branch: str,
) -> str | None:
    """查询远端文件 sha；文件不存在时返回 None。"""
    response = await client.get(api_url, headers=headers, params={"ref": branch})
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise GitHubSyncError(
            f"查询 GitHub 文件失败: HTTP {response.status_code} - {response.text}"
        )

    data = response.json()
    if data.get("type") != "file":
        raise GitHubSyncError("GitHub 目标路径已存在，但不是文件")
    sha = data.get("sha")
    if not isinstance(sha, str) or not sha:
        raise GitHubSyncError("GitHub API 未返回有效文件 sha")
    return sha
