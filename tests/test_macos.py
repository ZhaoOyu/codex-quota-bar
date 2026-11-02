"""Native component regression checks; requires a macOS desktop session."""
import sys
import time
import unittest
import uuid
from unittest.mock import patch


@unittest.skipUnless(sys.platform == "darwin", "AppKit requires macOS")
class NativePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import AppKit as A
        cls.appkit = A
        cls.app = A.NSApplication.sharedApplication()
        cls.app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)

    def setUp(self):
        from codex_quota_bar.controller import Controller
        from codex_quota_bar.macos import QuotaPanel
        self.controller = Controller(demo=True)
        self.panel = QuotaPanel.alloc().init()
        from Foundation import NSUserDefaults
        self.preference_suite = "io.github.codex-quota-bar.tests." + uuid.uuid4().hex
        self.preferences = NSUserDefaults.alloc().initWithSuiteName_(self.preference_suite)
        self.panel.configure(self.controller, self.preferences)

    def tearDown(self):
        self.preferences.removePersistentDomainForName_(self.preference_suite)
        self.panel.timer.invalidate()
        self.panel.popover.close()
        self.appkit.NSStatusBar.systemStatusBar().removeStatusItem_(self.panel.status)

    def test_native_icon_and_demo_identity(self):
        self.assertTrue(self.panel.button.image().isTemplate())
        self.assertEqual(self.panel.button.image().size(), (35, 24))
        self.assertIn("[演示]", self.panel.button.title())
        self.assertIn("02:34", self.panel.button.title())
        self.assertIn("[演示]", self.panel.button.accessibilityLabel())
        self.assertFalse(self.panel.refresh_button.isEnabled())
        self.assertEqual(self.panel.rows["five_hour"][0].stringValue(), "78%")
        self.assertAlmostEqual(self.panel.rows["weekly"][1].doubleValue(), 62)

    def test_weekly_only_resize_and_return(self):
        from codex_quota_bar.model import Quota
        original = self.controller.quota
        self.controller.quota = Quota(None, original.weekly, time.time())
        self.panel.tick_(None)
        self.assertEqual(list(self.panel.rows), ["weekly"])
        self.assertEqual(self.panel.height, 402)
        self.assertIn("天", self.panel.reset_value.stringValue())
        self.controller.quota = original
        self.panel.tick_(None)
        self.assertEqual(len(self.panel.rows), 2)
        self.assertEqual(self.panel.height, 490)

    def test_error_removes_previous_numbers(self):
        self.controller.demo = False
        self.controller.next_poll = time.time() + 60
        self.controller.quota = None
        self.controller.error = "额度读取失败；请运行 codex login。"
        self.panel.tick_(None)
        self.assertEqual(self.panel.rows["weekly"][0].stringValue(), "--")
        self.assertTrue(self.panel.rows["weekly"][1].isHidden())
        self.assertIn("codex login", self.panel.message.stringValue())
        self.assertTrue(self.panel.refresh_button.isEnabled())

    def test_expired_is_unknown_but_zero_is_measured(self):
        from codex_quota_bar.model import Quota, Window
        now = time.time()
        self.controller.quota = Quota(Window(0, now + 100), Window(62, now - 1), now)
        self.panel.tick_(None)
        self.assertEqual(self.panel.rows["five_hour"][0].stringValue(), "0%")
        self.assertFalse(self.panel.rows["five_hour"][1].isHidden())
        self.assertEqual(self.panel.rows["weekly"][0].stringValue(), "待刷新")
        self.assertTrue(self.panel.rows["weekly"][1].isHidden())

    def test_refresh_and_usage_actions(self):
        self.controller.next_poll = time.time() + 60
        with patch.object(self.controller, "refresh") as refresh:
            self.panel.refresh_(None)
            refresh.assert_called_once()
        with patch("codex_quota_bar.macos.webbrowser.open") as open_url:
            self.panel.usage_(None)
            open_url.assert_called_once_with("https://chatgpt.com/codex/settings/usage")

    def test_startup_action_does_not_write_in_test(self):
        with patch("codex_quota_bar.macos.startup.set_enabled") as setter, \
             patch("codex_quota_bar.macos.startup.is_enabled", return_value=True):
            self.panel.auto.setState_(1)
            self.panel.startup_(None)
            setter.assert_called_once_with(True)
            self.assertEqual(self.panel.auto.state(), 1)

    def test_stale_status_and_missing_reset(self):
        from codex_quota_bar.model import Quota, Window
        now = time.time()
        self.controller.demo = False
        self.controller.next_poll = now + 60
        self.controller.quota = Quota(None, Window(50, None), now - 181)
        self.panel.tick_(None)
        self.assertIn("数据已过期", self.panel.message.stringValue())
        self.assertEqual(self.panel.reset_value.stringValue(), "--:--")
        self.assertIn("!", self.panel.button.accessibilityLabel())

    def test_independent_choices_and_persistence(self):
        from Foundation import NSUserDefaults
        from codex_quota_bar.macos import selected_window
        quota_picker = self.panel.selectors["quotaWindow"]["weekly"]
        quota_picker.performClick_(None)
        self.assertEqual(self.preferences.stringForKey_("quotaWindow"), "weekly")
        self.assertIn("每周剩余 62%", self.panel.button.toolTip())
        self.assertIn("02:34", self.panel.button.title())
        time_picker = self.panel.selectors["countdownWindow"]["weekly"]
        time_picker.performClick_(None)
        self.assertIn("天", self.panel.button.title())
        reloaded = NSUserDefaults.alloc().initWithSuiteName_(self.preference_suite)
        self.assertEqual(selected_window(reloaded, "quotaWindow", self.controller.quota), "weekly")
        self.assertEqual(selected_window(reloaded, "countdownWindow", self.controller.quota), "weekly")
        self.panel.selectors["quotaWindow"]["five_hour"].performClick_(None)
        self.assertEqual(self.preferences.stringForKey_("quotaWindow"), "five_hour")
        self.assertEqual(self.preferences.stringForKey_("countdownWindow"), "weekly")
        self.assertEqual(quota_picker.state(), 0)
        self.assertEqual(self.panel.selectors["quotaWindow"]["five_hour"].state(), 1)
        self.panel.selectors["countdownWindow"]["five_hour"].performClick_(None)
        self.assertEqual(self.preferences.stringForKey_("countdownWindow"), "five_hour")
        self.assertEqual(time_picker.state(), 0)
        self.panel.selectors["countdownWindow"]["five_hour"].performClick_(None)
        self.assertEqual(self.panel.selectors["countdownWindow"]["five_hour"].state(), 1)
        self.assertEqual(self.preferences.stringForKey_("countdownWindow"), "five_hour")

    def test_missing_selected_window_does_not_switch_to_weekly(self):
        from codex_quota_bar.model import Quota
        self.preferences.setObject_forKey_("five_hour", "quotaWindow")
        self.preferences.setObject_forKey_("five_hour", "countdownWindow")
        self.controller.quota = Quota(None, self.controller.quota.weekly, time.time())
        self.panel.tick_(None)
        self.assertIn("五小时剩余 --", self.panel.button.toolTip())
        self.assertIn("--:--", self.panel.button.title())
        self.assertEqual(self.panel.selectors["quotaWindow"]["five_hour"].state(), 1)
        self.assertEqual(self.panel.selectors["quotaWindow"]["weekly"].state(), 0)

    def test_invalid_saved_selection_uses_available_window(self):
        from codex_quota_bar.macos import selected_window
        self.preferences.setObject_forKey_("obsolete", "quotaWindow")
        self.assertEqual(selected_window(self.preferences, "quotaWindow", self.controller.quota), "five_hour")

    def test_selected_expired_countdown_and_icon(self):
        from codex_quota_bar.model import Quota, Window
        now = time.time()
        self.preferences.setObject_forKey_("weekly", "quotaWindow")
        self.preferences.setObject_forKey_("weekly", "countdownWindow")
        self.controller.quota = Quota(Window(78, now + 3600), Window(62, now - 1), now)
        self.panel.tick_(None)
        self.assertIn("待刷新", self.panel.button.title())
        self.assertIn("每周剩余 待刷新", self.panel.button.toolTip())


if __name__ == "__main__":
    unittest.main()
