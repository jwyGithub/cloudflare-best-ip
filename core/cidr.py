"""
CIDR 处理：远程拉取 CIDR 列表，随机采样生成 ip:port 字符串。
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from models import Config
from utils import generate_random_ip_from_cidr, get_random_port

logger = logging.getLogger(__name__)


async def _fetch_with_retry(url: str, retries: int, timeout: float, retry_delay: float) -> str:
    """带重试的 HTTP GET，返回响应文本。"""
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(1, retries + 1):
            try:
                logger.debug("第 %d 次请求: %s", attempt, url)
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text
            except Exception as exc:
                last_error = exc
                logger.warning("请求失败 (第 %d/%d 次): %s — %s", attempt, retries, url, exc)
                if attempt < retries:
                    await asyncio.sleep(retry_delay)

    raise RuntimeError(f"请求 {url} 在 {retries} 次重试后仍失败") from last_error


async def process_cidr(ip_url: str, config: Config) -> list[str]:
    """
    拉取远程 CIDR 列表，随机采样直到凑满 config.total 个唯一 ip:port。

    Returns:
        list[str]: 形如 "1.2.3.4:443" 的字符串列表。
    """
    logger.info("获取 CIDR 列表开始: %s", ip_url)

    http = config.http
    text = await _fetch_with_retry(ip_url, http.retries, http.timeout, http.retry_delay)

    # 过滤空行和注释行
    cidrs = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    logger.info("解析到 CIDR 条目: %d 条", len(cidrs))

    if not cidrs:
        raise ValueError(f"CIDR 列表为空: {ip_url}")

    total = config.scan.total
    port_cfg = config.scan.port
    result: list[str] = []
    seen: set[str] = set()

    # port_cfg.default 用 is not None 判断，避免 0 被当作 falsy
    fixed_port = port_cfg.default if port_cfg.default is not None else None

    # 安全上限：最多循环 total * 10 次，防止 CIDR 空间不足时死循环
    max_attempts = total * 10
    attempts = 0

    while len(result) < total:
        if attempts >= max_attempts:
            logger.warning(
                "已达最大采样次数 %d，当前仅收集到 %d 个 IP（目标 %d）",
                max_attempts, len(result), total,
            )
            break
        for cidr in cidrs:
            if len(result) >= total:
                break
            attempts += 1
            ip = generate_random_ip_from_cidr(cidr)
            port = fixed_port if fixed_port is not None else get_random_port(port_cfg.list)
            entry = f"{ip}:{port}"
            if entry not in seen:
                seen.add(entry)
                result.append(entry)

    logger.info("CIDR 采样完成: 生成 %d 个 ip:port", len(result))
    return result
