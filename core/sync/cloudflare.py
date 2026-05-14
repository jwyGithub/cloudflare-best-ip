"""
Cloudflare DNS 同步：将本地输出文件中的 IP 同步为指定域名的 A 记录。
"""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Any

import httpx

from core.sync.base import SyncError
from models import CloudflareSyncConfig
from utils.logging import get_logger

logger = get_logger(__name__)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareDNSSyncError(SyncError):
    """Cloudflare DNS 同步失败。"""


async def sync_ips_to_cloudflare_dns(
    *,
    local_path: str | Path,
    token: str | None,
    sub_domain: str | None,
    limit: int,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """
    将输出文件中的 IP 同步到 Cloudflare DNS A 记录。

    同步策略：
    - 通过 token 获取账号下第一个 zone
    - 删除目标记录名下已有 A 记录
    - 为输出文件中的每个唯一 IP 创建一条新的 A 记录
    """
    if not token:
        raise CloudflareDNSSyncError("缺少 Cloudflare token，请传入 token")
    if not sub_domain:
        raise CloudflareDNSSyncError("缺少 Cloudflare 子域名配置，请设置 sub_domain")

    ips = _read_ips_from_output(local_path, limit=limit)
    if not ips:
        raise CloudflareDNSSyncError(f"输出文件中没有可同步的 IP: {Path(local_path).resolve()}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        zone_id, domain = await _get_zone(client=client, headers=headers)
        record_name = _build_record_name(sub_domain=sub_domain, domain=domain)
        records = await _list_dns_records(
            client=client,
            headers=headers,
            zone_id=zone_id,
            record_name=record_name,
        )

        logger.info("Cloudflare DNS 同步目标: {}，待删除 A 记录 {} 条", record_name, len(records))
        for record in records:
            await _delete_dns_record(
                client=client,
                headers=headers,
                zone_id=zone_id,
                record_id=record["id"],
            )
            logger.info("已删除 Cloudflare DNS 记录: {} -> {}", record["name"], record["content"])

        created_records: list[dict[str, Any]] = []
        for ip in ips:
            created = await _create_dns_record(
                client=client,
                headers=headers,
                zone_id=zone_id,
                record_name=record_name,
                ip=ip,
            )
            created_records.append(created)
            logger.info("已创建 Cloudflare DNS 记录: {} -> {}", record_name, ip)

    logger.info("Cloudflare DNS 同步完成: {}，创建 {} 条 A 记录", record_name, len(created_records))
    return {
        "zone_id": zone_id,
        "domain": domain,
        "record_name": record_name,
        "deleted": len(records),
        "created": len(created_records),
    }


async def sync_ips_to_cloudflare_dns_from_config(
    *,
    local_path: str | Path,
    config: CloudflareSyncConfig | None,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    """
    根据 Cloudflare 配置同步 DNS。

    配置不存在或未启用时返回 None，不执行同步。
    """
    if not config:
        logger.info("未配置 Cloudflare DNS 同步，跳过")
        return None
    if not config.enabled:
        logger.info("Cloudflare DNS 同步未启用，跳过")
        return None

    return await sync_ips_to_cloudflare_dns(
        local_path=local_path,
        token=config.token,
        sub_domain=config.sub_domain,
        limit=config.limit,
        timeout=timeout,
    )


def _read_ips_from_output(local_path: str | Path, *, limit: int) -> list[str]:
    """从输出文件读取唯一 IPv4，保持原始顺序。"""
    if limit <= 0:
        raise CloudflareDNSSyncError(f"Cloudflare DNS 同步数量限制必须大于 0: {limit}")

    source = Path(local_path)
    if not source.exists():
        raise CloudflareDNSSyncError(f"本地文件不存在: {source.resolve()}")
    if not source.is_file():
        raise CloudflareDNSSyncError(f"本地路径不是文件: {source.resolve()}")

    ips: list[str] = []
    seen: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value:
            continue
        ip_port = value.split("#", 1)[0]
        ip = ip_port.rsplit(":", 1)[0].strip()
        try:
            ipaddress.IPv4Address(ip)
        except ValueError as exc:
            raise CloudflareDNSSyncError(f"输出文件包含无效 IPv4: {ip}") from exc
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)
            if len(ips) >= limit:
                break
    return ips


async def _get_zone(
    *,
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> tuple[str, str]:
    """获取 Cloudflare 账号下第一个 zone 的 ID 和域名。"""
    data = await _request_json(
        client,
        "GET",
        f"{CLOUDFLARE_API_BASE}/zones",
        headers=headers,
    )
    zones = data.get("result") or []
    if not zones:
        raise CloudflareDNSSyncError("未找到 Cloudflare 域区")

    zone = zones[0]
    zone_id = zone.get("id")
    domain = zone.get("name")
    if not zone_id or not domain:
        raise CloudflareDNSSyncError("Cloudflare API 未返回有效域区信息")
    return str(zone_id), str(domain)


def _build_record_name(*, sub_domain: str, domain: str) -> str:
    """根据子域名和 zone 域名生成完整 DNS 记录名。"""
    normalized_sub = sub_domain.strip().strip(".")
    normalized_domain = domain.strip().strip(".")
    if normalized_sub == "@":
        return normalized_domain
    if normalized_sub == normalized_domain or normalized_sub.endswith(f".{normalized_domain}"):
        return normalized_sub
    return f"{normalized_sub}.{normalized_domain}"


async def _list_dns_records(
    *,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    zone_id: str,
    record_name: str,
) -> list[dict[str, Any]]:
    """分页读取目标记录名下所有 A 记录。"""
    page = 1
    per_page = 100
    records: list[dict[str, Any]] = []

    while True:
        data = await _request_json(
            client,
            "GET",
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
            headers=headers,
            params={
                "type": "A",
                "page": page,
                "per_page": per_page,
                "name": record_name,
            },
        )
        records.extend(data.get("result") or [])
        total_pages = data.get("result_info", {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return records


async def _delete_dns_record(
    *,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    zone_id: str,
    record_id: str,
) -> None:
    """删除一条 DNS 记录。"""
    await _request_json(
        client,
        "DELETE",
        f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}",
        headers=headers,
    )


async def _create_dns_record(
    *,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    zone_id: str,
    record_name: str,
    ip: str,
) -> dict[str, Any]:
    """创建一条 A 记录。"""
    data = await _request_json(
        client,
        "POST",
        f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
        headers=headers,
        json={
            "type": "A",
            "name": record_name,
            "content": ip,
            "ttl": 1,
            "proxied": False,
        },
    )
    result = data.get("result")
    if not isinstance(result, dict):
        raise CloudflareDNSSyncError("Cloudflare API 未返回有效 DNS 记录")
    return result


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """执行 Cloudflare API 请求并校验标准响应。"""
    response = await client.request(method, url, **kwargs)
    if response.status_code >= 400:
        raise CloudflareDNSSyncError(
            f"Cloudflare API 请求失败: HTTP {response.status_code} - {response.text}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise CloudflareDNSSyncError(f"Cloudflare API 返回非 JSON 响应: {response.text}") from exc

    if not data.get("success", False):
        raise CloudflareDNSSyncError(f"Cloudflare API 返回失败: {data.get('errors', [])}")
    return data
