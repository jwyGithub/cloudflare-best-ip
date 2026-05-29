from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from utils.logging import get_logger, setup_logging


class LoggingTests(unittest.TestCase):
    def test_non_tty_stderr_does_not_emit_ansi_color_codes(self) -> None:
        stream = io.StringIO()

        with patch("sys.stderr", stream):
            logger = setup_logging()
            logger.info("普通日志")
            get_logger("best.test").opt(colors=True).info(
                "彩色 <green><bold>日志</bold></green>"
            )

        output = stream.getvalue()
        self.assertNotIn("\x1b[", output)
        self.assertIn("普通日志", output)
        self.assertIn("彩色 日志", output)


if __name__ == "__main__":
    unittest.main()
