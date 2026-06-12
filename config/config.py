"""
类化配置定义。

EnvConfig 负责读取环境变量，各领域配置类负责持有默认值并解析出最终值，
AppConfig 负责组合为程序运行使用的 models.Config。
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from pydantic import BaseModel, Field

from config.source_loader import load_builtin_sources
from models import (
    CloudflareSyncConfig as RuntimeCloudflareSyncConfig,
    Config as RuntimeConfig,
    GitHubSyncConfig as RuntimeGitHubSyncConfig,
    HttpConfig as RuntimeHttpConfig,
    LogConfig as RuntimeLogConfig,
    OutputConfig as RuntimeOutputConfig,
    ScanConfig as RuntimeScanConfig,
    ScheduleConfig as RuntimeScheduleConfig,
    SyncConfig as RuntimeSyncConfig,
)


def _env_value(name: str) -> str | None:
    """读取环境变量，未设置或空白时返回 None。"""
    raw = os.getenv(name)
    if raw is None:
        return None

    value = raw.strip()
    return value or None


def _parse_positive_int(name: str, value: str | None) -> int | None:
    """解析正整数环境变量值。"""
    if value is None:
        return None

    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 环境变量必须是正整数: {value}") from exc

    if number <= 0:
        raise ValueError(f"{name} 环境变量必须大于 0: {number}")
    return number


class EnvConfig(BaseModel):
    """环境变量快照。"""

    scan_source: str | None = None
    scan_port: str | None = None
    scan_concurrency: str | None = None
    scan_total: str | None = None
    scan_output_path: str | None = None
    scan_output_limit: str | None = None
    schedule_cron: str | None = None
    schedule_timezone: str | None = None
    log_level: str | None = None
    sync_github_owner: str | None = None
    sync_github_repo: str | None = None
    sync_github_branch: str | None = None
    sync_github_remote_path: str | None = None
    sync_github_token: str | None = None
    sync_cloudflare_sub_domain: str | None = None
    sync_cloudflare_token: str | None = None
    sync_cloudflare_limit: str | None = None

    @classmethod
    def from_os(cls) -> "EnvConfig":
        """从当前进程环境变量生成配置快照。"""
        return cls(
            scan_source=_env_value("SCAN_SOURCE"),
            scan_port=_env_value("SCAN_PORT"),
            scan_concurrency=_env_value("SCAN_CONCURRENCY"),
            scan_total=_env_value("SCAN_TOTAL"),
            scan_output_path=_env_value("SCAN_OUTPUT_PATH"),
            scan_output_limit=_env_value("SCAN_OUTPUT_LIMIT"),
            schedule_cron=_env_value("SCHEDULE_CRON"),
            schedule_timezone=_env_value("SCHEDULE_TIMEZONE"),
            log_level=_env_value("LOG_LEVEL"),
            sync_github_owner=_env_value("SYNC_GITHUB_OWNER"),
            sync_github_repo=_env_value("SYNC_GITHUB_REPO"),
            sync_github_branch=_env_value("SYNC_GITHUB_BRANCH"),
            sync_github_remote_path=_env_value("SYNC_GITHUB_REMOTE_PATH"),
            sync_github_token=_env_value("SYNC_GITHUB_TOKEN"),
            sync_cloudflare_sub_domain=_env_value("SYNC_CLOUDFLARE_SUB_DOMAIN"),
            sync_cloudflare_token=_env_value("SYNC_CLOUDFLARE_TOKEN"),
            sync_cloudflare_limit=_env_value("SYNC_CLOUDFLARE_LIMIT"),
        )

    def scan_sources(self) -> list[str] | None:
        if self.scan_source is None:
            return None

        sources = [item.strip() for item in self.scan_source.split(",") if item.strip()]
        return sources or None

    def scan_ports(self) -> list[int] | None:
        if self.scan_port is None:
            return None

        ports: list[int] = []
        for value in self.scan_port.split(","):
            try:
                port = int(value.strip())
            except ValueError:
                continue

            if 1 <= port <= 65535:
                ports.append(port)

        return ports or None


class SourceConfig(BaseModel):
    """内置 CIDR 源配置。"""

    source_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "source")
    default_source: str = "cloudflare"
    sources: dict[str, list[str]] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        if not self.sources:
            self.sources = load_builtin_sources(self.source_dir)

    def resolve_sources(self, env: EnvConfig) -> list[str]:
        return env.scan_sources() or [self.default_source]


class PortConfig(BaseModel):
    """扫描端口配置。"""

    ports: list[int] = Field(
        default_factory=lambda: [443, 2053, 2083, 2087, 2096, 8443]
    )

    def resolve_ports(self, env: EnvConfig) -> list[int]:
        return env.scan_ports() or self.ports


class ScanConfig(BaseModel):
    """扫描行为配置。"""

    concurrency: int = 8
    total: int = 512
    test_url: str = "https://{hex_ip}.nip.cmliussss.hidns.vip:{port}/ip.json"

    def resolve_concurrency(self, env: EnvConfig) -> int:
        return (
            _parse_positive_int("SCAN_CONCURRENCY", env.scan_concurrency)
            or self.concurrency
        )

    def resolve_total(self, env: EnvConfig) -> int:
        return _parse_positive_int("SCAN_TOTAL", env.scan_total) or self.total


class OutputConfig(BaseModel):
    """输出配置。"""

    path: str = "output/ips.txt"
    limit: int = 60

    def resolve_path(self, env: EnvConfig) -> str:
        return env.scan_output_path or self.path

    def resolve_limit(self, env: EnvConfig) -> int:
        return (
            _parse_positive_int("SCAN_OUTPUT_LIMIT", env.scan_output_limit)
            or self.limit
        )


class LogConfig(BaseModel):
    """日志配置。"""

    level: str = "INFO"
    file: str | None = None

    def resolve_level(self, env: EnvConfig) -> str:
        return env.log_level or self.level


class HttpConfig(BaseModel):
    """HTTP 请求配置。"""

    timeout: int = 5
    retries: int = 3
    retry_delay: float = 1.0


class ScheduleConfig(BaseModel):
    """定时执行配置。"""

    cron: str = "0 6 * * *"
    timezone: str = "Asia/Shanghai"

    def resolve_cron(self, env: EnvConfig) -> str:
        return env.schedule_cron or self.cron

    def resolve_timezone(self, env: EnvConfig) -> str:
        return env.schedule_timezone or self.timezone


class GitHubSyncConfig(BaseModel):
    """GitHub 同步配置。"""

    enabled: bool = False
    owner: str | None = None
    repo: str | None = None
    remote_path: str = "ips.txt"
    branch: str = "main"
    token: str | None = None

    def resolve(self, env: EnvConfig) -> RuntimeGitHubSyncConfig:
        owner = env.sync_github_owner or self.owner
        repo = env.sync_github_repo or self.repo
        branch = env.sync_github_branch or self.branch
        remote_path = env.sync_github_remote_path or self.remote_path
        token = env.sync_github_token or self.token
        enabled = all([owner, repo, branch, remote_path, token])

        return RuntimeGitHubSyncConfig(
            enabled=enabled,
            owner=owner,
            repo=repo,
            remote_path=remote_path,
            branch=branch,
            token=token,
            commit_message=f"chore: update ips.txt on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        )


class CloudflareSyncConfig(BaseModel):
    """Cloudflare DNS 同步配置。"""

    enabled: bool = False
    sub_domain: str = "@"
    token: str | None = None
    limit: int = 10

    def resolve(self, env: EnvConfig) -> RuntimeCloudflareSyncConfig:
        token = env.sync_cloudflare_token or self.token
        return RuntimeCloudflareSyncConfig(
            enabled=bool(token),
            sub_domain=env.sync_cloudflare_sub_domain or self.sub_domain,
            token=token,
            limit=_parse_positive_int(
                "SYNC_CLOUDFLARE_LIMIT",
                env.sync_cloudflare_limit,
            )
            or self.limit,
        )


class SyncConfig(BaseModel):
    """同步配置。"""

    github: GitHubSyncConfig = Field(default_factory=GitHubSyncConfig)
    cloudflare: CloudflareSyncConfig = Field(default_factory=CloudflareSyncConfig)

    def resolve(self, env: EnvConfig) -> RuntimeSyncConfig:
        return RuntimeSyncConfig(
            github=self.github.resolve(env),
            cloudflare=self.cloudflare.resolve(env),
        )


class AppConfig(BaseModel):
    """应用配置组合器。"""

    source: SourceConfig = Field(default_factory=SourceConfig)
    port: PortConfig = Field(default_factory=PortConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)

    def resolve(self, env: EnvConfig) -> RuntimeConfig:
        """解析为业务运行使用的 Config 模型。"""
        return RuntimeConfig(
            scan=RuntimeScanConfig(
                sources=self.source.resolve_sources(env),
                ports=self.port.resolve_ports(env),
                concurrency=self.scan.resolve_concurrency(env),
                total=self.scan.resolve_total(env),
                test_url=self.scan.test_url,
            ),
            output=RuntimeOutputConfig(
                path=self.output.resolve_path(env),
                limit=self.output.resolve_limit(env),
            ),
            log=RuntimeLogConfig(
                level=self.log.resolve_level(env),
                file=self.log.file,
            ),
            http=RuntimeHttpConfig(
                timeout=self.http.timeout,
                retries=self.http.retries,
                retry_delay=self.http.retry_delay,
            ),
            schedule=RuntimeScheduleConfig(
                cron=self.schedule.resolve_cron(env),
                timezone=self.schedule.resolve_timezone(env),
            ),
            sync=self.sync.resolve(env),
        )
