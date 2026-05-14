"""
程序入口：加载配置 → 解析内置 CIDR → 测试 IP → 查询地理信息 → 写出文本文件。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from config import load_config, resolve_scan_cidrs
from core.cidr import process_cidr
from core.geo import batch_geo_lookup
from core.sync import SyncError, sync_ips_from_config
from core.test import test_ips
from utils.logging import get_logger, log_config_summary, setup_logging
from utils.signal_handler import setup_signal_handlers


async def main() -> None:
    # 设置信号处理器
    setup_signal_handlers()

    config = load_config()

    setup_logging(level=config.log.level, log_file=config.log.file)
    logger = get_logger("best.main")

    log_config_summary(logger, config)

    try:
        cidrs = resolve_scan_cidrs(config)
    except ValueError as exc:
        logger.error("{}", exc)
        sys.exit(1)

    ips = await process_cidr(cidrs, config)

    results = await test_ips(ips, config)

    if not results:
        logger.warning("没有测试通过的 IP，跳过写出")
        return

    limit = config.output.limit
    top = sorted(results, key=lambda r: r.avg_time)[:limit]

    unique_ips = list({r.ip for r in top})
    geo_map = await batch_geo_lookup(unique_ips, config.geo)

    output_path = Path(__file__).parent / config.output.path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for r in top:
        geo = geo_map.get(r.ip)
        label = geo.label if geo and geo.status == "success" else r.colo
        lines.append(f"{r.ip}:{r.port}#{label}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info(
        "结果已写入: {}  (共 {} 条，限制 {} 条)",
        output_path, len(lines), limit,
    )

    try:
        await sync_ips_from_config(
            local_path=output_path,
            config=config.sync,
        )
    except SyncError as exc:
        logger.error("同步失败: {}", exc)


if __name__ == "__main__":
    asyncio.run(main())
