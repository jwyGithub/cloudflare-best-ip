from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from config import load_config, resolve_scan_cidrs
from config.config import AppConfig, EnvConfig
from models import ScanConfig as RuntimeScanConfig


class ConfigLoadingTests(unittest.TestCase):
    def test_default_config_uses_class_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        self.assertEqual(config.scan.sources, ["cloudflare"])
        self.assertEqual(config.scan.ports, [443, 2053, 2083, 2087, 2096, 8443])
        self.assertEqual(config.scan.concurrency, 8)
        self.assertEqual(config.scan.total, 512)
        self.assertEqual(config.scan.cfdata_bin, "cfdata")
        self.assertEqual(config.scan.scan_mode, "tcping")
        self.assertTrue(config.scan.enable_tls)
        self.assertEqual(config.scan.delay_threshold, 500)
        self.assertEqual(config.scan.speed_url, "auto")
        self.assertEqual(config.scan.speed_test_threads, 1)
        self.assertEqual(config.scan.speed_min, 0.1)
        self.assertEqual(config.scan.speed_limit, 5)
        self.assertEqual(config.output.path, "output/ips.txt")
        self.assertEqual(config.output.limit, 60)
        self.assertEqual(config.log.level, "INFO")
        self.assertIsNone(config.log.file)
        self.assertEqual(config.http.timeout, 5)
        self.assertEqual(config.http.retries, 3)
        self.assertEqual(config.http.retry_delay, 1.0)
        self.assertEqual(config.schedule.cron, "0 6 * * *")
        self.assertEqual(config.schedule.timezone, "Asia/Shanghai")
        self.assertIsNotNone(config.sync)
        self.assertIsNotNone(config.sync.github)
        self.assertFalse(config.sync.github.enabled)
        self.assertIsNotNone(config.sync.cloudflare)
        self.assertFalse(config.sync.cloudflare.enabled)

    def test_env_config_treats_blank_values_as_unset(self) -> None:
        with patch.dict(
            os.environ,
            {"SCAN_SOURCE": "  ", "SCAN_PORT": "\t", "SCAN_CONCURRENCY": ""},
            clear=True,
        ):
            env = EnvConfig.from_os()

        self.assertIsNone(env.scan_source)
        self.assertIsNone(env.scan_port)
        self.assertIsNone(env.scan_concurrency)

    def test_scan_source_and_port_env_override_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SCAN_SOURCE": "cm",
                "SCAN_PORT": "443,8443",
                "SCAN_CONCURRENCY": "2",
                "SCAN_TOTAL": "30",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.scan.sources, ["cm"])
        self.assertEqual(config.scan.ports, [443, 8443])
        self.assertEqual(config.scan.concurrency, 2)
        self.assertEqual(config.scan.total, 30)
        self.assertEqual(len(resolve_scan_cidrs(config)), len(AppConfig().source.sources["cm"]))

    def test_invalid_scan_port_falls_back_to_default_pool(self) -> None:
        with patch.dict(os.environ, {"SCAN_PORT": "abc,70000"}, clear=True):
            config = load_config()

        self.assertEqual(config.scan.ports, [443, 2053, 2083, 2087, 2096, 8443])

    def test_positive_integer_env_vars_raise_for_invalid_values(self) -> None:
        with patch.dict(os.environ, {"SCAN_CONCURRENCY": "0"}, clear=True):
            with self.assertRaisesRegex(ValueError, "SCAN_CONCURRENCY 环境变量必须大于 0"):
                load_config()

        with patch.dict(os.environ, {"SCAN_TOTAL": "many"}, clear=True):
            with self.assertRaisesRegex(ValueError, "SCAN_TOTAL 环境变量必须是正整数"):
                load_config()

    def test_sync_env_rules_match_existing_behavior(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SYNC_GITHUB_OWNER": "owner",
                "SYNC_GITHUB_REPO": "repo",
                "SYNC_GITHUB_BRANCH": "main",
                "SYNC_GITHUB_REMOTE_PATH": "ips.txt",
                "SYNC_GITHUB_TOKEN": "gh-token",
                "SYNC_CLOUDFLARE_TOKEN": "cf-token",
            },
            clear=True,
        ):
            config = load_config()

        self.assertTrue(config.sync.github.enabled)
        self.assertEqual(config.sync.github.owner, "owner")
        self.assertTrue(config.sync.cloudflare.enabled)
        self.assertEqual(config.sync.cloudflare.sub_domain, "@")
        self.assertEqual(config.sync.cloudflare.limit, 10)

    def test_app_config_exposes_loaded_sources_for_resolution(self) -> None:
        app_config = AppConfig()

        self.assertIn("cloudflare", app_config.source.sources)
        self.assertIn("cm", app_config.source.sources)

    def test_cfdata_env_overrides_scan_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "CFDATA_BIN": "/usr/local/bin/cfdata",
                "SCAN_MODE": "httping",
                "SCAN_ENABLE_TLS": "false",
                "DELAY_THRESHOLD": "300",
                "SPEED_URL": "speed.cloudflare.com/__down?bytes=99999999",
                "SPEED_TEST_THREADS": "0",
                "SPEED_MIN": "1.5",
                "SPEED_LIMIT": "0",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.scan.cfdata_bin, "/usr/local/bin/cfdata")
        self.assertEqual(config.scan.scan_mode, "httping")
        self.assertFalse(config.scan.enable_tls)
        self.assertEqual(config.scan.delay_threshold, 300)
        self.assertEqual(config.scan.speed_url, "speed.cloudflare.com/__down?bytes=99999999")
        self.assertEqual(config.scan.speed_test_threads, 0)
        self.assertEqual(config.scan.speed_min, 1.5)
        self.assertEqual(config.scan.speed_limit, 0)

    def test_runtime_scan_config_defaults(self) -> None:
        scan = RuntimeScanConfig()
        self.assertEqual(scan.cfdata_bin, "cfdata")
        self.assertEqual(scan.scan_mode, "tcping")
        self.assertEqual(scan.speed_test_threads, 1)


if __name__ == "__main__":
    unittest.main()
