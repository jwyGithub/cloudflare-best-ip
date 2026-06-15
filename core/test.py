"""
IP 测试：并发测试 ip:port 的可用性和延迟，通过 /ip.json 获取 colo 信息。
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Optional

import httpx

from models import Config, TestResult
from utils import ip_to_hex
from utils.logging import get_logger

logger = get_logger(__name__)


def _parse_ip_entry(entry: str) -> tuple[str, str, str]:
    """解析 "ip:port" 或 "ip:port#remark" 格式，返回 (ip, port, remark)。"""
    remark = ""
    if "#" in entry:
        ip_port, remark = entry.split("#", 1)
    else:
        ip_port = entry
    ip, port = ip_port.rsplit(":", 1)
    return ip, port, remark

def _with_cache_buster(url: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}_t={int(time.time() * 1000)}"


async def _test_options_connectivity(
    url: str,
    client: httpx.AsyncClient,
    timeout_seconds: float,
) -> bool:
    """按 JS 版本逻辑执行 OPTIONS 连通性预检，最多尝试 3 次。"""
    for attempt in range(3):
        try:
            resp = await client.options(url, timeout=timeout_seconds * 2)
            if resp.is_success:
                return True
            logger.debug("OPTIONS 预检失败: {} (HTTP {}, 第 {} 次)", url, resp.status_code, attempt + 1)
        except Exception as exc:
            logger.debug("OPTIONS 预检异常: {} (第 {} 次): {}", url, attempt + 1, exc)
    return False


async def _test_single_ip(
    entry: str,
    client: httpx.AsyncClient,
    test_url_tpl: str,
    timeout_seconds: float,
) -> Optional[TestResult]:
    """
    测试单个 ip:port：先 OPTIONS 预检，再对单次 GET /ip.json 计时。

    使用外部传入的 AsyncClient 以复用连接池，避免每次重建开销。
    test_url_tpl 来自 config.scan.test_url，含 {hex_ip} 和 {port} 占位符。
    """
    ip, port, remark = _parse_ip_entry(entry)
    hex_ip = ip_to_hex(ip)
    base_url = test_url_tpl.format(hex_ip=hex_ip, port=port)

    url = _with_cache_buster(base_url)
    if not await _test_options_connectivity(url, client, timeout_seconds):
        logger.debug("IP {}:{} OPTIONS 预检不可用", ip, port)
        return None

    try:
        start = time.perf_counter()
        resp = await client.get(url, timeout=timeout_seconds)
        if not resp.is_success:
            logger.debug("IP {}:{} GET 请求失败 (HTTP {})", ip, port, resp.status_code)
            return None
        trace_data = resp.json()
        elapsed = max(1, round((time.perf_counter() - start) * 1000))
    except Exception as exc:
        logger.debug("IP {}:{} GET 请求异常: {}", ip, port, exc)
        return None

    if elapsed > timeout_seconds * 1000:
        logger.debug("IP {}:{} 延迟超过超时时间: {}ms", ip, port, elapsed)
        return None

    result = TestResult(
        ip=ip,
        port=port,
        remark=remark,
        response_ip=trace_data.get("ip", ip),
        colo=trace_data.get("colo", ""),
        avg_time=elapsed,
    )
    logger.info(
        "测试成功  {}:{} - 响应 {}ms, colo={}, 响应 IP: {}",
        ip, port, elapsed, result.colo, result.response_ip,
    )
    return result


async def test_ips(ips: List[str], config: Config) -> List[TestResult]:
    """
    并发测试所有 ip:port，按 config.scan.concurrency 控制并发度。

    使用共享 AsyncClient（连接复用）+ asyncio.Semaphore（并发限制）。
    任务通过 asyncio.as_completed 流式消费，避免一次性创建全部协程的内存峰值。
    """
    total = len(ips)
    concurrency = config.scan.concurrency
    timeout = httpx.Timeout(float(config.http.timeout))
    test_url_tpl = config.scan.test_url

    logger.info("[在线优选] 开始: 总计 {} 个 IP，并发度 {}", total, concurrency)

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
                res = await _test_single_ip(entry, client, test_url_tpl, float(config.http.timeout))
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
            logger.debug("进度: {} / {}", done, total)

    logger.info("[在线优选] 完成: 总计={} 成功={} 失败={}", total, success, fail)
    return results
