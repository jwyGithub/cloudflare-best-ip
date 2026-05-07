"""
程序入口：加载配置 → 拉取 CIDR → 测试 IP → 查询地理信息 → 写出文本文件。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from config import load_config
from utils.logging import setup_logging, get_logger
from core.cidr import process_cidr
from core.test import test_ips
from core.geo import batch_geo_lookup


async def main() -> None:
    # ── 加载配置 ────────────────────────────────────────────────
    config_path = Path(__file__).parent / "config" / "config.yaml"
    config = load_config(config_path)

    # ── 初始化日志（必须在使用任何 logger 之前）──────────────────
    setup_logging(level=config.log.level, log_file=config.log.file)
    logger = get_logger("best.main")

    logger.info("配置加载成功:\n%s", config.model_dump_json(indent=4))

    # ── 选取 IP 源（取 cm-list）────────────────────────────────
    ip_key = "cm-list"
    ip_url = config.scan.sources.get(ip_key)
    if not ip_url:
        logger.error("配置中找不到 ip 源: %s", ip_key)
        sys.exit(1)

    # ── 拉取 CIDR 并生成 ip:port 列表 ─────────────────────────
    ips = await process_cidr(ip_url, config)

    # ── 并发测试 ────────────────────────────────────────────────
    results = await test_ips(ips, config)

    if not results:
        logger.warning("没有测试通过的 IP，跳过写出")
        return

    # ── 按延迟排序，取前 limit 条 ─────────────────────────────
    limit = config.output.limit
    top = sorted(results, key=lambda r: r.avg_time)[:limit]

    # ── 批量查询地理信息 ────────────────────────────────────────
    unique_ips = list({r.ip for r in top})
    geo_map = await batch_geo_lookup(unique_ips, config.geo)

    # ── 写出文本文件，每行格式：ip:port#(countryCode-region) ───
    output_path = Path(__file__).parent / config.output.path
    lines: list[str] = []
    for r in top:
        geo = geo_map.get(r.ip)
        label = geo.label if geo and geo.status == "success" else r.colo
        lines.append(f"{r.ip}:{r.port}#{label}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info(
        "结果已写入: %s  (共 %d 条，限制 %d 条)",
        output_path, len(lines), limit,
    )


if __name__ == "__main__":
    asyncio.run(main())
