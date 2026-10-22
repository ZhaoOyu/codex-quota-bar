from pathlib import Path
import sys
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_quota_bar.client import Rpc, UsageError, fetch_quota, find_codex, child_environment

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

    def test_missing_node_error_is_actionable_without_leaking_stderr(self):
        with self.connect("missing-node") as rpc:
            with self.assertRaises(UsageError) as caught:
                self.initialize(rpc)
        self.assertIn("Node.js", str(caught.exception))
        self.assertNotIn("secret-token", str(caught.exception))
        self.assertFalse(rpc.error_reader.is_alive())

    def test_stderr_is_drained_without_blocking_protocol(self):
        with self.connect("stderr-flood") as rpc:
            self.initialize(rpc)
            self.assertIn("rateLimits", rpc.request("account/rateLimits/read"))

    def test_gui_path_finds_node_outside_codex_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = root / "homebrew" / "node"
            node.parent.mkdir()
            node.write_text("#!/bin/sh\nexit 0\n")
            node.chmod(0o755)
            with patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}), \
                 patch("codex_quota_bar.client.cli_directories", return_value=[node.parent]):
                env = child_environment(str(root / "npm-global/bin/codex"))
            import subprocess
            result = subprocess.run(["/usr/bin/env", "node"], env=env, timeout=2)
            self.assertEqual(result.returncode, 0)

    def test_fetch_uses_default_stdio_without_newer_listen_flag(self):
        with patch("codex_quota_bar.client.find_codex", return_value=sys.executable), \
             patch("codex_quota_bar.client.Rpc", side_effect=lambda _: self.connect()) as factory:
            fetch_quota()
        factory.assert_called_once_with([sys.executable, "app-server"])


if __name__ == "__main__":
    unittest.main()

