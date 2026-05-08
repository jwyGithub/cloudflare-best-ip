"""
CIDR 处理：从内置 CIDR 列表随机采样生成 ip:port 字符串。
"""

from __future__ import annotations

from models import Config
from utils import generate_random_ip_from_cidr, get_random_port
from utils.logging import get_logger

logger = get_logger(__name__)


async def process_cidr(cidrs: list[str], config: Config) -> list[str]:
    """
    从 CIDR 列表随机采样，直到凑满 config.total 个唯一 ip:port。

    Returns:
        list[str]: 形如 "1.2.3.4:443" 的字符串列表。
    """
    logger.info("加载 CIDR 条目: {} 条", len(cidrs))

    if not cidrs:
        raise ValueError("CIDR 列表为空")

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
                "已达最大采样次数 {}，当前仅收集到 {} 个 IP（目标 {}）",
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

    logger.info("CIDR 采样完成: 生成 {} 个 ip:port", len(result))
    return result
