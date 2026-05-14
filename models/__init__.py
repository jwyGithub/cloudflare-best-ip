"""
数据模型：项目所有 Pydantic 数据模型。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ScanConfig(BaseModel):
    """IP 扫描相关配置：来源、端口、并发、采样数量。"""
    sources: List[str] = Field(default_factory=lambda: ["cloudflare"])  # 内置 IP 源名称列表
    ports: List[int] = Field(default_factory=lambda: [443, 2053, 2083, 2087, 2096, 8443])
    concurrency: int = 8            # 并发测试协程数
    total: int = 512                # 从 CIDR 采样的 IP 总数
    # {hex_ip} 和 {port} 为占位符，运行时动态替换
    test_url: str = "https://{hex_ip}.nip.lfree.org:{port}/cdn-cgi/trace"


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


class GeoConfig(BaseModel):
    url: str = "http://ip-api.com/batch"
    batch_limit: int = 100
    fields: str = "status,countryCode,region,query"
    timeout: float = 10.0
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
    geo: GeoConfig = Field(default_factory=GeoConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    sync: Optional[SyncConfig] = None


class TestResult(BaseModel):
    ip: str
    port: str
    remark: str = ""
    response_ip: str
    colo: str
    avg_time: int  # ms


class ColoGroup(BaseModel):
    colo: str
    ips: List[TestResult]
