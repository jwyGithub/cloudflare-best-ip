"""
数据模型：项目所有 Pydantic 数据模型。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ScanConfig(BaseModel):
    """IP 扫描相关配置：来源、端口、并发、采样数量，以及 CFData CLI 测速参数。"""
    sources: List[str] = Field(default_factory=lambda: ["cloudflare"])  # 内置 IP 源名称列表
    ports: List[int] = Field(default_factory=lambda: [443, 2053, 2083, 2087, 2096, 8443])
    concurrency: int = 8            # CFData 非标扫描线程数（-nsbthreads）
    total: int = 512                # 从 CIDR 采样的 IP 总数

    # CFData CLI 相关配置（替代原先的 URL 测速）
    cfdata_bin: str = "cfdata"      # CFData 可执行文件路径或名称（在 PATH 中）
    scan_mode: str = "tcping"       # 延迟测试方式：tcping / httping
    enable_tls: bool = True         # 非标是否启用 TLS（-nsbtls）
    delay_threshold: int = 500      # 延迟阈值，单位毫秒（-nsbdelay）
    result_limit: int = 1000        # 延迟测试结果上限（-nsbresultlimit）
    speed_url: str = "auto"         # 测速下载地址；auto 由 CFData 自动选择（-nsburl）
    speed_test_threads: int = 1     # 测速线程数，0 表示不测速（-nsbspeedtest）
    speed_min: float = 0.1          # 测速合格阈值，单位 MB/s（-nsbspeedmin）
    speed_limit: int = 5            # 测速合格结果上限（-nsbspeedlimit）


class OutputConfig(BaseModel):
    path: str = "output/ips.txt"
    limit: int = 60


class LogConfig(BaseModel):
    level: str = "INFO"
    file: Optional[str] = None


class HttpConfig(BaseModel):
    timeout: int = 5
    retries: int = 3
    retry_delay: float = 1.0


class ScheduleConfig(BaseModel):
    cron: str = "0 6 * * *"    # cron 表达式，默认 Asia/Shanghai 每天 06:00
    timezone: str = "Asia/Shanghai"  # IANA 时区名称


class GitHubSyncConfig(BaseModel):
    enabled: bool = False
    owner: Optional[str] = None
    repo: Optional[str] = None
    remote_path: str = "ips.txt"
    branch: str = "main"
    token: Optional[str] = None
    commit_message: str = "chore: update ips.txt"


class CloudflareSyncConfig(BaseModel):
    enabled: bool = False
    sub_domain: str = "@"
    token: Optional[str] = None
    limit: int = 10


class SyncConfig(BaseModel):
    github: Optional[GitHubSyncConfig] = None
    cloudflare: Optional[CloudflareSyncConfig] = None


class Config(BaseModel):
    scan: ScanConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    sync: Optional[SyncConfig] = None


class TestResult(BaseModel):
    ip: str
    port: str
    remark: str = ""
    response_ip: str
    colo: str
    avg_time: int  # ms（网络延迟）
    loss_rate: float = 0.0   # 丢包率，0~1
    speed: float = 0.0       # 下载速度，单位 MB/s，0 表示未测速
    region: str = ""         # 地区
    city: str = ""           # 城市


class ColoGroup(BaseModel):
    colo: str
    ips: List[TestResult]
