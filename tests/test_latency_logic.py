from __future__ import annotations

import unittest

from core.test import _test_single_ip


class FakeResponse:
    def __init__(self, *, status_code: int = 200, data: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._data = data or {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict[str, str]:
        return self._data


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def options(self, url: str, **_: object) -> FakeResponse:
        self.calls.append(("OPTIONS", url))
        return FakeResponse()

    async def get(self, url: str, **_: object) -> FakeResponse:
        self.calls.append(("GET", url))
        return FakeResponse(data={"ip": "203.0.113.8", "colo": "SJC"})


class LatencyLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_ip_matches_js_options_probe_then_one_get(self) -> None:
        client = FakeClient()

        result = await _test_single_ip(
            "1.2.3.4:443#remark",
            client,  # type: ignore[arg-type]
            "https://{hex_ip}.nip.cmliussss.hidns.vip:{port}/ip.json",
            timeout_seconds=5,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual([method for method, _ in client.calls], ["OPTIONS", "GET"])
        self.assertEqual(result.ip, "1.2.3.4")
        self.assertEqual(result.port, "443")
        self.assertEqual(result.remark, "remark")
        self.assertEqual(result.response_ip, "203.0.113.8")
        self.assertEqual(result.colo, "SJC")
        self.assertGreaterEqual(result.avg_time, 1)
        for _, url in client.calls:
            self.assertTrue(url.startswith("https://01020304.nip.cmliussss.hidns.vip:443/ip.json?_t="))


if __name__ == "__main__":
    unittest.main()
