"""
IP 地理信息查询：通过 ip-api.com/batch 批量获取 IP 的 countryCode / region。
"""

from __future__ import annotations

from typing import Any, Dict, List

import httpx
from pydantic import BaseModel

from models import TestResult
from utils.logging import get_logger

logger = get_logger(__name__)


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
        return self.country_code


async def batch_geo_lookup(
    ips: List[TestResult]
) -> Dict[str, GeoInfo]:
    """
    Returns:
        dict[ip -> GeoInfo]，方便 O(1) 取值。
    """
    logger.info("开始批量查询地理信息: 共 {} 个 IP", len(ips))

    result: Dict[str, GeoInfo] = {}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get('https://speed.cloudflare.com/locations',headers={
            'Referer': 'https://speed.cloudflare.com/'
        })
        resp.raise_for_status()
        data: List[Dict[str, Any]] = resp.json()
        for item in ips:
            location = next((loc for loc in data if loc['iata'] == item.colo), None)
            if location:
                result[item.ip] = GeoInfo(
                    query=item.ip,
                    status="success",
                    country_code=location['cca2'],
                    region=location['region'],
                )
            else:
                result[item.ip] = GeoInfo(
                    query=item.ip,
                    status="success",
                    country_code=item.colo,
                    region='',
                )

    success = sum(1 for v in result.values() if v.status == "success")
    logger.info("地理信息查询完成: 成功 {} / 总计 {}", success, len(ips))
    return result
