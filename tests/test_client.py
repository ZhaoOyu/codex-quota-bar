from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from codex_quota_bar.client import Rpc, UsageError, fetch_quota, find_codex

FIXTURE = str(Path(__file__).with_name("fake_codex.py"))


class ClientTests(unittest.TestCase):
    def connect(self, mode="ok", timeout=2):
        return Rpc([sys.executable, FIXTURE, mode], timeout=timeout)

    def initialize(self, rpc):
        rpc.request("initialize", {"clientInfo": {"name": "codex_quota_bar"}})
        rpc.send({"method": "initialized"})

    def test_process_protocol_and_cleanup(self):
        with self.connect() as rpc:
            self.initialize(rpc)
            result = rpc.request("account/rateLimits/read")
            self.assertEqual(result["rateLimits"]["primary"]["usedPercent"], 22)
        self.assertIsNotNone(rpc.process.poll())
        self.assertFalse(rpc.reader.is_alive())

    def test_fetch_integration(self):
        # Real subprocess and transport, substituting only the executable.
        with patch("codex_quota_bar.client.find_codex", return_value=sys.executable), \
             patch("codex_quota_bar.client.Rpc", side_effect=lambda _: self.connect()):
            quota = fetch_quota()
        self.assertEqual(quota.five_hour.remaining, 78)
        self.assertEqual(quota.weekly.remaining, 62)

    def test_timeout_terminates_child(self):
        with self.connect("timeout", timeout=0.2) as rpc:
            self.initialize(rpc)
            with self.assertRaisesRegex(UsageError, "超时"):
                rpc.request("account/rateLimits/read")
        self.assertIsNotNone(rpc.process.poll())

    def test_server_error_does_not_leak(self):
        with self.connect("error") as rpc:
            self.initialize(rpc)
            with self.assertRaises(UsageError) as caught:
                rpc.request("account/rateLimits/read")
            self.assertNotIn("secret-token", str(caught.exception))

    def test_process_exit(self):
        with self.connect("exit") as rpc:
            self.initialize(rpc)
            with self.assertRaisesRegex(UsageError, "提前退出"):
                rpc.request("account/rateLimits/read")

    def test_invalid_path(self):
        with self.assertRaisesRegex(UsageError, "路径无效"):
            find_codex("/nonexistent/codex")


if __name__ == "__main__":
    unittest.main()

