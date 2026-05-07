"""
IP 测试：并发测试 ip:port 的可用性和延迟，通过 cdn-cgi/trace 获取 colo 信息。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

import httpx

from models import Config, TestResult
from utils import ip_to_hex

logger = logging.getLogger(__name__)


def _parse_ip_entry(entry: str) -> tuple[str, str, str]:
    """解析 "ip:port" 或 "ip:port#remark" 格式，返回 (ip, port, remark)。"""
    remark = ""
    if "#" in entry:
        ip_port, remark = entry.split("#", 1)
    else:
        ip_port = entry
    ip, port = ip_port.rsplit(":", 1)
    return ip, port, remark


def _parse_trace(text: str) -> dict[str, str]:
    """解析 Cloudflare cdn-cgi/trace 的 key=value 格式响应。"""
    data: dict[str, str] = {}
    for line in text.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


async def _test_single_ip(
    entry: str, client: httpx.AsyncClient, test_url_tpl: str
) -> Optional[TestResult]:
    """
    测试单个 ip:port，共请求 3 次，丢弃第 1 次（DNS 预热），取后 2 次均值。

    使用外部传入的 AsyncClient 以复用连接池，避免每次重建开销。
    test_url_tpl 来自 config.scan.test_url，含 {hex_ip} 和 {port} 占位符。
    """
    ip, port, remark = _parse_ip_entry(entry)
    hex_ip = ip_to_hex(ip)
    base_url = test_url_tpl.format(hex_ip=hex_ip, port=port)

    times: list[float] = []
    trace_data: Optional[dict[str, str]] = None

    for i in range(3):
        url = f"{base_url}?_t={int(time.time() * 1000)}"
        try:
            start = time.perf_counter()
            resp = await client.get(url)
            elapsed = (time.perf_counter() - start) * 1000  # ms

            if not resp.is_success:
                if i == 0:
                    logger.debug("IP %s:%s 首次请求失败 (HTTP %d)", ip, port, resp.status_code)
                    return None
                continue

            # 第 0 次：解析 trace body，不计入延迟（DNS 预热）
            # 第 1、2 次：计入延迟，无需重复解析 body
            if i == 0:
                trace_data = _parse_trace(resp.text)
            else:
                times.append(elapsed)

        except Exception as exc:
            if i == 0:
                logger.debug("IP %s:%s 首次请求异常: %s", ip, port, exc)
                return None
            logger.debug("IP %s:%s 第 %d 次请求异常: %s", ip, port, i + 1, exc)

    if trace_data is None or not times:
        return None

    avg_time = round(sum(times) / len(times))
    result = TestResult(
        ip=ip,
        port=port,
        remark=remark,
        response_ip=trace_data.get("ip", ip),
        colo=trace_data.get("colo", ""),
        avg_time=avg_time,
    )
    logger.info(
        "测试成功  %s:%s — 平均响应 %dms, colo=%s",
        ip, port, avg_time, result.colo,
    )
    return result


async def test_ips(ips: List[str], config: Config) -> List[TestResult]:
    """
    并发测试所有 ip:port，按 config.thread 控制并发度。

    使用共享 AsyncClient（连接复用）+ asyncio.Semaphore（并发限制）。
    任务通过 asyncio.as_completed 流式消费，避免一次性创建全部协程的内存峰值。
    """
    total = len(ips)
    concurrency = config.scan.thread
    timeout = httpx.Timeout(float(config.http.timeout))
    test_url_tpl = config.scan.test_url

    logger.info("[在线优选] 开始: 总计 %d 个 IP，并发度 %d", total, concurrency)

    results: list[TestResult] = []
    success = 0
    fail = 0
    # asyncio 单线程下 list.append 是原子的，Lock 用于未来兼容真多线程
    lock = asyncio.Lock()

    semaphore = asyncio.Semaphore(concurrency)

    # 所有协程共享一个 AsyncClient，复用底层 TCP 连接池
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=concurrency * 2,
            max_keepalive_connections=concurrency,
        ),
    ) as client:

        async def _bounded(entry: str) -> None:
            nonlocal success, fail
            async with semaphore:
                res = await _test_single_ip(entry, client, test_url_tpl)
            async with lock:
                if res:
                    results.append(res)
                    success += 1
                else:
                    fail += 1

        # 分批提交：每批 concurrency*4 个任务，避免 512 个协程同时挂起
        batch_size = concurrency * 4
        for batch_start in range(0, total, batch_size):
            batch = ips[batch_start : batch_start + batch_size]
            tasks = [asyncio.create_task(_bounded(ip)) for ip in batch]
            for coro in asyncio.as_completed(tasks):
                await coro
            done = batch_start + len(batch)
            logger.debug("进度: %d / %d", done, total)

    logger.info("[在线优选] 完成: 总计=%d 成功=%d 失败=%d", total, success, fail)
    return results
