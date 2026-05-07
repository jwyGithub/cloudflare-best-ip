"""
IP 地理信息查询：通过 ip-api.com/batch 批量获取 IP 的 countryCode / region。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel

from models import GeoConfig

logger = logging.getLogger(__name__)


class GeoInfo(BaseModel):
    query: str          # 查询的 IP
    status: str         # "success" | "fail"
    country_code: str = ""
    region: str = ""

    @property
    def label(self) -> str:
        """生成 remark 标签，格式：(CN-GD) 或 (US)。"""
        if not self.country_code:
            return ""
        if self.region:
            return f"{self.country_code}-{self.region}"
        return f"({self.country_code})"


async def _query_batch(
    client: httpx.AsyncClient,
    ips: List[str],
    cfg: GeoConfig,
) -> List[GeoInfo]:
    """单批查询，失败时重试，返回与入参等长的 GeoInfo 列表。"""
    payload = [{"query": ip, "fields": cfg.fields} for ip in ips]
    last_exc: Optional[Exception] = None

    for attempt in range(1, cfg.retries + 1):
        try:
            resp = await client.post(cfg.url, json=payload, timeout=cfg.timeout)
            resp.raise_for_status()
            raw = resp.json()
            return [
                GeoInfo(
                    query=item.get("query", ""),
                    status=item.get("status", "fail"),
                    country_code=item.get("countryCode", ""),
                    region=item.get("region", ""),
                )
                for item in raw
            ]
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "ip-api.com 批量查询失败 (第 %d/%d 次): %s", attempt, cfg.retries, exc
            )
            if attempt < cfg.retries:
                await asyncio.sleep(cfg.retry_delay)

    logger.error("ip-api.com 批量查询最终失败，本批 %d 个 IP 地理信息留空: %s", len(ips), last_exc)
    return [GeoInfo(query=ip, status="fail") for ip in ips]


async def batch_geo_lookup(
    ips: List[str],
    cfg: GeoConfig,
) -> Dict[str, GeoInfo]:
    """
    批量查询所有 IP 的地理信息，自动按 cfg.batch_limit 分批。

    Returns:
        dict[ip -> GeoInfo]，方便 O(1) 取值。
    """
    logger.info("开始批量查询地理信息: 共 %d 个 IP", len(ips))

    result: Dict[str, GeoInfo] = {}
    batches = [ips[i : i + cfg.batch_limit] for i in range(0, len(ips), cfg.batch_limit)]

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for idx, batch in enumerate(batches, 1):
            logger.debug("geo 批次 %d/%d: %d 个 IP", idx, len(batches), len(batch))
            infos = await _query_batch(client, batch, cfg)
            for info in infos:
                result[info.query] = info

    success = sum(1 for v in result.values() if v.status == "success")
    logger.info("地理信息查询完成: 成功 %d / 总计 %d", success, len(ips))
    return result
