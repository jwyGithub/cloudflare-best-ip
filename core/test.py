"""
IP 测试：调用 CFData CLI（非标 / nsb 模式）测试 ip:port 的延迟、丢包率与下载速度，
解析其导出的 CSV 结果为 TestResult 列表。

替代了旧的「拼接 hex_ip 域名 + OPTIONS 预检 + 单次 GET 计时」逻辑。
CFData 项目地址：https://github.com/PoemMisty/CFData-WEB
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
from pathlib import Path
from typing import List, Optional

from models import Config, TestResult
from utils.logging import get_logger

logger = get_logger(__name__)

# 传给 CFData `-fields` 的导出字段（小写），CFData 会按此顺序输出 CSV 列。
# 解析时按 _CFDATA_COLUMNS 的顺序（大小写为 CFData 内部 key）读取。
_CFDATA_FIELDS = "ip,port,latency,lossrate,speed,dc,outboundip,region,city"
_CFDATA_COLUMNS = [
    "ip",
    "port",
    "latency",
    "lossRate",
    "speed",
    "dc",
    "outboundIP",
    "region",
    "city",
]

# CFData 的工作目录名（存放输入/输出/配置及本地缓存，缓存跨次运行复用）
_WORKDIR_NAME = ".cfdata"


def _parse_ip_entry(entry: str) -> tuple[str, str]:
    """解析 "ip:port" 或 "ip:port#remark" 格式，返回 (ip, port)。"""
    ip_port = entry.split("#", 1)[0]
    ip, port = ip_port.rsplit(":", 1)
    return ip, port


def _parse_latency_ms(value: str) -> Optional[int]:
    """解析形如 "123ms" 的延迟字符串为毫秒整数。"""
    value = value.strip().lower().removesuffix("ms").strip()
    if not value:
        return None
    try:
        return max(1, round(float(value)))
    except ValueError:
        return None


def _parse_speed_mb(value: str) -> float:
    """解析形如 "5.20MB/s" 的速度字符串为 MB/s 浮点数；无法解析返回 0。"""
    value = value.strip()
    if not value or "MB/s" not in value:
        return 0.0
    try:
        return float(value.replace("MB/s", "").strip())
    except ValueError:
        return 0.0


def _parse_loss_rate(value: str) -> float:
    """解析形如 "25%" 的丢包率字符串为 0~1 的浮点数。"""
    value = value.strip().rstrip("%").strip()
    if not value:
        return 0.0
    try:
        return float(value) / 100.0
    except ValueError:
        return 0.0


def _build_workdir() -> Path:
    """创建并返回 CFData 工作目录（当前工作目录下的 .cfdata）。"""
    workdir = Path.cwd() / _WORKDIR_NAME
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _ensure_cfdata_config(config_path: Path) -> None:
    """
    确保 CFData CLI 配置文件存在。

    CFData 在配置文件不存在时会「生成模板并退出」，因此这里预先写入一个最小配置，
    保证 CLI 每次都能直接执行（所有实际参数由命令行传入，优先级最高）。
    """
    if config_path.exists():
        return
    config_path.write_text(json.dumps({"cli": True}), encoding="utf-8")


def _write_nsb_input(ips: List[str], path: Path) -> int:
    """把采样得到的 ip:port 列表写为 CFData 非标输入格式（每行 "ip port"）。"""
    lines: list[str] = []
    for entry in ips:
        try:
            ip, port = _parse_ip_entry(entry)
        except ValueError:
            logger.debug("跳过无法解析的条目: {}", entry)
            continue
        lines.append(f"{ip} {port}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def _build_cfdata_args(config: Config, in_path: Path, out_name: str, config_path: Path) -> list[str]:
    """构造 CFData CLI 非标模式的命令行参数。"""
    scan = config.scan
    return [
        "-cli",
        "-mode", "nsb",
        "-nsbfile", str(in_path),
        "-nsbout", out_name,
        "-nsbthreads", str(scan.concurrency),
        "-scanmode", scan.scan_mode,
        f"-nsbtls={'true' if scan.enable_tls else 'false'}",
        "-nsbdelay", str(scan.delay_threshold),
        "-nsbresultlimit", str(max(scan.result_limit, config.output.limit)),
        "-nsbspeedtest", str(scan.speed_test_threads),
        "-nsbspeedmin", str(scan.speed_min),
        "-nsbspeedlimit", str(scan.speed_limit),
        "-nsbqualified=false",
        "-nsburl", scan.speed_url,
        "-format", "csv",
        "-fields", _CFDATA_FIELDS,
        "-nocolor",
        "-config", str(config_path),
    ]


def _parse_cfdata_csv(content: str) -> List[TestResult]:
    """解析 CFData 导出的 CSV 内容（列顺序由 _CFDATA_COLUMNS 决定）为 TestResult 列表。"""
    # 去除可能的 UTF-8 BOM
    content = content.lstrip("﻿")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return []

    results: List[TestResult] = []
    # 第一行是表头（中文标签），跳过
    for row in rows[1:]:
        if len(row) < len(_CFDATA_COLUMNS):
            logger.debug("跳过列数不足的 CSV 行: {}", row)
            continue
        record = dict(zip(_CFDATA_COLUMNS, row))

        avg_time = _parse_latency_ms(record.get("latency", ""))
        if avg_time is None:
            logger.debug("跳过无有效延迟的行: {}", record)
            continue

        ip = record.get("ip", "").strip()
        port = record.get("port", "").strip()
        if not ip or not port:
            continue

        results.append(
            TestResult(
                ip=ip,
                port=port,
                remark="",
                response_ip=record.get("outboundIP", "").strip() or ip,
                colo=record.get("dc", "").strip(),
                avg_time=avg_time,
                loss_rate=_parse_loss_rate(record.get("lossRate", "")),
                speed=_parse_speed_mb(record.get("speed", "")),
                region=record.get("region", "").strip(),
                city=record.get("city", "").strip(),
            )
        )
    return results


async def test_ips(ips: List[str], config: Config) -> List[TestResult]:
    """
    调用 CFData CLI（非标模式）测试所有 ip:port，返回 TestResult 列表。

    流程：
      1. 把采样出的 ip:port 写入 CFData 非标输入文件（每行 "ip port"）；
      2. 以子进程方式调用 CFData CLI，导出 CSV；
      3. 解析 CSV 为 TestResult（延迟、丢包率、下载速度、数据中心、地区等）。

    仅返回通过延迟测试的结果（CFData 已自动过滤失败项）。
    """
    total = len(ips)
    if total == 0:
        logger.warning("没有待测试的 IP")
        return []

    scan = config.scan
    workdir = _build_workdir()
    config_path = workdir / "cfdata-config.json"
    in_path = workdir / "nsb-input.txt"
    out_name = "nsb-output.csv"
    out_path = workdir / out_name

    _ensure_cfdata_config(config_path)
    written = _write_nsb_input(ips, in_path)

    # 清理上次的输出，避免解析到旧结果
    if out_path.exists():
        out_path.unlink()

    args = _build_cfdata_args(config, in_path, out_name, config_path)

    logger.info(
        "[CFData 优选] 开始: 总计 {} 个 IP，扫描方式={}，并发={}，测速线程={}",
        written, scan.scan_mode, scan.concurrency, scan.speed_test_threads,
    )
    logger.debug("CFData 命令: {} {}", scan.cfdata_bin, " ".join(args))

    try:
        proc = await asyncio.create_subprocess_exec(
            scan.cfdata_bin,
            *args,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        logger.error(
            "找不到 CFData 可执行文件: {}（请通过 CFDATA_BIN 指定路径，或将其加入 PATH）",
            scan.cfdata_bin,
        )
        return []

    # 保守超时：随 IP 数量增长，最少 5 分钟，最多约 1 小时
    timeout = min(3600, max(300, total * 3))

    async def _stream_output() -> None:
        """实时读取 CFData 子进程输出并逐行打印（测速进度可见）。

        CFData 的进度更新常用回车 \\r 覆盖同一行而非换行，因此这里同时按
        \\r 和 \\n 切分，保证进度能实时刷出，而不是等到进程结束才一次性输出。
        """
        assert proc.stdout is not None
        buf = ""
        while True:
            chunk = await proc.stdout.read(1024)
            if not chunk:
                tail = buf.strip()
                if tail:
                    logger.info("[CFData] {}", tail)
                break
            buf += chunk.decode("utf-8", errors="replace")
            parts = re.split(r"[\r\n]+", buf)
            buf = parts.pop()  # 末段可能不完整，留到下次
            for part in parts:
                part = part.strip()
                if part:
                    logger.info("[CFData] {}", part)

    try:
        await asyncio.wait_for(
            asyncio.gather(_stream_output(), proc.wait()), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("CFData 执行超时（>{}s），终止进程", timeout)
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        return []

    if proc.returncode != 0:
        logger.error("CFData 退出码非 0: {}", proc.returncode)

    if not out_path.exists():
        logger.warning("CFData 未生成结果文件: {}", out_path)
        return []

    content = out_path.read_text(encoding="utf-8", errors="replace")
    results = _parse_cfdata_csv(content)

    logger.info(
        "[CFData 优选] 完成: 总计={} 通过={} 失败={}",
        total, len(results), total - len(results),
    )
    return results
