from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from codex_quota_bar import startup


class StartupTests(unittest.TestCase):
    def test_explicit_cli_preserved_without_demo_flags(self):
        with patch.object(startup.sys, "argv", ["app", "--codex", "/my/bin/codex", "--demo"]), \
             patch("codex_quota_bar.client.find_codex", return_value="/my/bin/codex"):
            command = startup.launch_command()
            self.assertEqual(command[-2:], ["--codex", "/my/bin/codex"])
            self.assertNotIn("--demo", command)

    def test_linux_registration_and_removal(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(startup, "startup_path", return_value=Path(directory) / "test.desktop"), \
             patch.object(startup.sys, "platform", "linux"), \
             patch.object(startup, "launch_command", return_value=["/app with space/bin", "100%"]):
            startup.set_enabled(True)
            self.assertTrue(startup.is_enabled())
            self.assertIn('Exec="/app with space/bin" "100%%"', startup.startup_path().read_text())
            startup.set_enabled(False)
            self.assertFalse(startup.is_enabled())

    def test_macos_registration(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(startup, "startup_path", return_value=Path(directory) / "test.plist"), \
             patch.object(startup.sys, "platform", "darwin"), \
             patch.object(startup, "launch_command", return_value=["/Applications/Codex Quota Bar.app/bin"]):
            startup.set_enabled(True)
            data = plistlib.loads(startup.startup_path().read_bytes())
            self.assertTrue(data["RunAtLoad"])
            self.assertEqual(data["ProgramArguments"], startup.launch_command())
