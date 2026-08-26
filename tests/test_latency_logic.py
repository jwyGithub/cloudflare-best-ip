from __future__ import annotations

import unittest

from core.test import (
    _parse_cfdata_csv,
    _parse_ip_entry,
    _parse_latency_ms,
    _parse_loss_rate,
    _parse_speed_mb,
    _write_nsb_input,
)


class ValueParsingTests(unittest.TestCase):
    def test_parse_ip_entry(self) -> None:
        self.assertEqual(_parse_ip_entry("1.2.3.4:443"), ("1.2.3.4", "443"))
        self.assertEqual(_parse_ip_entry("1.2.3.4:8443#CN-GD"), ("1.2.3.4", "8443"))

    def test_parse_latency_ms(self) -> None:
        self.assertEqual(_parse_latency_ms("123ms"), 123)
        self.assertEqual(_parse_latency_ms("0ms"), 1)  # 最小 1ms
        self.assertIsNone(_parse_latency_ms(""))
        self.assertIsNone(_parse_latency_ms("N/A"))

    def test_parse_speed_mb(self) -> None:
        self.assertEqual(_parse_speed_mb("5.20MB/s"), 5.20)
        self.assertEqual(_parse_speed_mb(""), 0.0)
        self.assertEqual(_parse_speed_mb("测速失败"), 0.0)

    def test_parse_loss_rate(self) -> None:
        self.assertEqual(_parse_loss_rate("0%"), 0.0)
        self.assertEqual(_parse_loss_rate("25%"), 0.25)
        self.assertEqual(_parse_loss_rate(""), 0.0)


class NSBInputWritingTests(unittest.TestCase):
    def test_write_nsb_input_converts_ip_port_lines(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            count = _write_nsb_input(["1.2.3.4:443", "5.6.7.8:8443#x"], path)
            self.assertEqual(count, 2)
            self.assertEqual(
                path.read_text(encoding="utf-8").strip().splitlines(),
                ["1.2.3.4 443", "5.6.7.8 8443"],
            )


class CFDataCSVParsingTests(unittest.TestCase):
    def test_parse_cfdata_csv_maps_all_fields(self) -> None:
        # 列顺序：ip,port,latency,lossRate,speed,dc,outboundIP,region,city
        content = (
            "﻿IP地址,端口号,网络延迟,丢包率,下载速度,数据中心,出站IP,地区,城市\n"
            "1.2.3.4,443,123ms,0%,5.20MB/s,SJC,203.0.113.8,North America,San Jose\n"
            "5.6.7.8,8443,88ms,25%,,LAX,203.0.113.9,North America,Los Angeles\n"
        )
        results = _parse_cfdata_csv(content)
        self.assertEqual(len(results), 2)

        first = results[0]
        self.assertEqual(first.ip, "1.2.3.4")
        self.assertEqual(first.port, "443")
        self.assertEqual(first.avg_time, 123)
        self.assertEqual(first.loss_rate, 0.0)
        self.assertEqual(first.speed, 5.20)
        self.assertEqual(first.colo, "SJC")
        self.assertEqual(first.response_ip, "203.0.113.8")
        self.assertEqual(first.region, "North America")
        self.assertEqual(first.city, "San Jose")

        second = results[1]
        self.assertEqual(second.avg_time, 88)
        self.assertEqual(second.loss_rate, 0.25)
        self.assertEqual(second.speed, 0.0)  # 未测速

    def test_parse_cfdata_csv_skips_invalid_rows(self) -> None:
        content = (
            "IP地址,端口号,网络延迟,丢包率,下载速度,数据中心,出站IP,地区,城市\n"
            "1.2.3.4,443,,0%,,SJC,203.0.113.8,NA,SJ\n"  # 无延迟，跳过
            "9.9.9.9,443,50ms,0%,,NRT,203.0.113.1,Asia,Tokyo\n"
        )
        results = _parse_cfdata_csv(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ip, "9.9.9.9")

    def test_parse_cfdata_csv_empty(self) -> None:
        self.assertEqual(_parse_cfdata_csv(""), [])


if __name__ == "__main__":
    unittest.main()
