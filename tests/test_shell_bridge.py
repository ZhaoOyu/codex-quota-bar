"""Real asynchronous session D-Bus tests; use dbus-run-session and Xvfb in CI."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch


@unittest.skipUnless(sys.platform.startswith("linux") and os.environ.get("DISPLAY")
                     and os.environ.get("DBUS_SESSION_BUS_ADDRESS"), "Requires GTK and session D-Bus")
class ShellBridgeTests(unittest.TestCase):
    def setUp(self):
        from codex_quota_bar.linux import Gtk, QuotaPanel
        from codex_quota_bar.controller import Controller
        from codex_quota_bar.linux_display import Preferences
        from codex_quota_bar.shell_bridge import ShellBridge, Gio, GLib
        if not Gtk.init_check()[0]:
            self.skipTest("GTK display unavailable")
        self.Gio, self.GLib = Gio, GLib
        self.temp = tempfile.TemporaryDirectory()
        prefs = Preferences(Path(self.temp.name) / "prefs.json")
        prefs.set("interfaceLanguage", "zh-Hans")
        with patch("codex_quota_bar.linux.startup.is_enabled", return_value=False):
            self.panel = QuotaPanel(Controller(demo=True), prefs, indicator_id="test-" + uuid.uuid4().hex)
        self.name = "io.github.ZhaoOyu.Test" + uuid.uuid4().hex
        self.bridge = ShellBridge(self.panel, self.name)
        self.panel.shell_bridge = self.bridge
        self.client = Gio.DBusConnection.new_for_address_sync(os.environ["DBUS_SESSION_BUS_ADDRESS"],
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
            None, None)
        self.pump(lambda: self.bridge.connection.get_unique_name() is not None, minimum=.05)

    def tearDown(self):
        if hasattr(self, "panel"):
            self.panel.close()
            if not self.client.is_closed():
                self.client.close_sync(None)
            self.temp.cleanup()

    def pump(self, done, minimum=0):
        start = time.monotonic()
        while time.monotonic() - start < 4:
            while self.GLib.MainContext.default().pending():
                self.GLib.MainContext.default().iteration(False)
            if done() and time.monotonic() - start >= minimum:
                return
            time.sleep(.005)
        self.fail("Timed out waiting for session D-Bus")

    def call(self, method, signature=None, values=()):
        from codex_quota_bar.shell_bridge import OBJECT_PATH, INTERFACE
        result = []
        def finish(connection, pending):
            try:
                result.append(connection.call_finish(pending).unpack())
            except self.GLib.Error as error:
                result.append(error)
        self.client.call(self.name, OBJECT_PATH, INTERFACE, method,
            self.GLib.Variant(signature, values) if signature else None, None,
            self.Gio.DBusCallFlags.NONE, 2500, None, finish)
        self.pump(lambda: bool(result))
        if isinstance(result[0], Exception):
            raise result[0]
        return result[0]

    def test_display_snapshot_and_selection(self):
        state = json.loads(self.call("GetState")[0])
        self.assertEqual(state["protocol"], 1)
        self.assertEqual(state["sections"][0]["value"], "78%")
        self.assertNotIn("codex", state)  # No CLI path or credentials.
        self.call("SetPreference", "(ss)", ("indicatorStyle", "track"))
        self.call("SetPreference", "(ss)", ("quotaWindow", "weekly"))
        state = json.loads(self.call("GetState")[0])
        self.assertEqual(state["style"], "track")
        self.assertIn("W 62", state["reading"])
        self.call("TogglePart", "(u)", (2,))
        self.assertNotIn("02:34", json.loads(self.call("GetState")[0])["reading"])

    def test_claim_release_and_lease_expiry(self):
        from codex_quota_bar.linux import AppIndicator
        self.call("Claim")
        self.assertEqual(self.panel.indicator.get_status(), AppIndicator.IndicatorStatus.PASSIVE)
        self.bridge.expires = time.monotonic() - 1
        self.panel.tick()
        self.assertEqual(self.panel.indicator.get_status(), AppIndicator.IndicatorStatus.ACTIVE)
        self.call("Claim")
        self.call("Release")
        self.assertIsNone(self.bridge.peer)

    def test_disconnect_restores_tray(self):
        self.call("Claim")
        self.client.close_sync(None)
        self.pump(lambda: self.bridge.peer is None)

    def test_invalid_actions_and_startup(self):
        for method, sig, values in (("TogglePart", "(u)", (4,)),
                                   ("SetPreference", "(ss)", ("shell", "bad"))):
            with self.assertRaises(self.GLib.Error):
                self.call(method, sig, values)
        with patch("codex_quota_bar.linux.startup.set_enabled") as setter, \
             patch("codex_quota_bar.linux.startup.is_enabled", return_value=True):
            self.call("SetStartup", "(b)", (True,))
            setter.assert_called_once_with(True)

    def test_state_signals_and_language(self):
        from codex_quota_bar.shell_bridge import INTERFACE, OBJECT_PATH
        states = []
        signal = self.client.signal_subscribe(self.name, INTERFACE, "StateChanged", OBJECT_PATH,
            None, self.Gio.DBusSignalFlags.NONE, lambda *args: states.append(json.loads(args[-1].unpack()[0])))
        try:
            self.call("SetPreference", "(ss)", ("interfaceLanguage", "en"))
            self.pump(lambda: bool(states))
            self.assertEqual(states[-1]["title"], "Codex Quota · Demo")
        finally:
            self.client.signal_unsubscribe(signal)
