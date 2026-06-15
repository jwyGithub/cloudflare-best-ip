"""
通用工具函数：CIDR 随机 IP 生成、端口选取、IP 转十六进制。
"""

from __future__ import annotations

import ipaddress
import random


def generate_random_ip_from_cidr(cidr: str) -> str:
    """在给定 CIDR 网段内随机生成一个 IPv4 地址。"""
    network = ipaddress.IPv4Network(cidr, strict=False)
    # network_address 和 broadcast_address 各占一个，直接用随机整数偏移
    host_count = network.num_addresses
    offset = random.randint(0, host_count - 1)
    ip_int = int(network.network_address) + offset
    return str(ipaddress.IPv4Address(ip_int))


def get_random_port(ports: list[int]) -> int:
    """从端口列表中随机返回一个端口。"""
    return random.choice(ports)


def ip_to_hex(ip: str) -> str:
    """将点分十进制 IPv4 地址转换为 JS 版本一致的 8 位大写十六进制标签。"""
    return "".join(f"{int(octet):02X}" for octet in ip.split("."))
