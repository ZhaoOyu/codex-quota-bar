"""Portable icon/preferences checks and native GTK interaction checks under Xvfb."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
import xml.etree.ElementTree as ET

from codex_quota_bar.display import choose_window, fraction
from codex_quota_bar.linux_display import Preferences, status_svg, indicator_track_svg
from codex_quota_bar.model import Quota, Window


class LinuxDisplayTests(unittest.TestCase):
    def test_track_icon_is_square_and_does_not_embed_text(self):
        for value in (None, 0, 0.62, 1):
            root = ET.fromstring(indicator_track_svg(value))
            self.assertEqual((root.get("width"), root.get("height")), ("24", "24"))
            self.assertNotIn("<text", indicator_track_svg(value))
            self.assertEqual(len(root.findall(".//{*}polygon")), 2 if value else 1)

    def test_preferences_round_trip_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config/prefs.json"
            prefs = Preferences(path)
            prefs.set("quotaWindow", "weekly")
            prefs.set("countdownWindow", "five_hour")
            self.assertEqual(Preferences(path).values, prefs.values)
            with self.assertRaises(ValueError):
                prefs.set("quotaWindow", "other")
            self.assertEqual(Preferences(path).get("quotaWindow"), "weekly")

    def test_malformed_preferences_and_failed_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            for content in ('{broken', '[]', '{"quotaWindow": "obsolete"}'):
                path.write_text(content)
                self.assertEqual(Preferences(path).values, {})
            prefs = Preferences(path)
            prefs.set("quotaWindow", "weekly")
            with patch("codex_quota_bar.linux_display.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    prefs.set("quotaWindow", "five_hour")
            self.assertEqual(Preferences(path).get("quotaWindow"), "weekly")
            self.assertEqual(prefs.get("quotaWindow"), "weekly")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_window_choice_and_missing_data(self):
        quota = Quota(None, Window(62, 200), 100)
        self.assertEqual(choose_window(None, quota), "weekly")
        self.assertEqual(choose_window("five_hour", quota), "five_hour")
        self.assertIsNone(fraction(None, 100))
        self.assertIsNone(fraction(Window(62, 100), 100))
        self.assertEqual(fraction(Window(0, 200), 100), 0)

    def test_svg_values_markers_and_unknown(self):
        ns = {"s": "http://www.w3.org/2000/svg"}
        for choice, marker in (("weekly", "W"), ("five_hour", "H")):
            for window, value in ((Window(78.9, 200), "78"), (Window(100, 200), "100"),
                                  (Window(0, 200), "0"), (Window(62, 100), "--"), (None, "--")):
                svg = status_svg(window, 100, choice)
                root = ET.fromstring(svg)
                self.assertEqual([text.text for text in root.findall(".//s:text", ns)], [value, marker])
                self.assertNotIn("%", svg)
                self.assertEqual('data-unknown' in svg, value == "--")


@unittest.skipUnless(sys.platform.startswith("linux") and bool(os.environ.get("DISPLAY")),
                     "Native GTK checks require Linux and DISPLAY (use xvfb-run)")
class LinuxPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from codex_quota_bar.linux import Gtk
        if not Gtk.init_check()[0]:
            raise unittest.SkipTest("GTK display unavailable")
        cls.Gtk = Gtk

    def setUp(self):
        from codex_quota_bar.controller import Controller
        from codex_quota_bar.linux import QuotaPanel
        self.directory = tempfile.TemporaryDirectory()
        self.preferences = Preferences(Path(self.directory.name) / "prefs.json")
        self.preferences.set("interfaceLanguage", "zh-Hans")
        self.controller = Controller(demo=True)
        with patch("codex_quota_bar.linux.startup.is_enabled", return_value=False):
            self.panel = QuotaPanel(self.controller, self.preferences,
                                   indicator_id="codex-quota-test-" + uuid.uuid4().hex)

    def tearDown(self):
        self.panel.close()
        self.directory.cleanup()
        while self.Gtk.events_pending():
            self.Gtk.main_iteration_do(False)

    def test_language_switch_keeps_quota_and_updates_menu(self):
        panel = self.panel
        quota = self.controller.quota
        panel.languages.set_active_id("en")
        self.assertEqual(panel.header.get_text(), "Codex Quota · Demo")
        self.assertTrue(panel.menu_info["weekly"].get_label().startswith("Weekly quota remaining"))
        self.assertEqual(panel.menu_refresh.get_label(), "Refresh now")
        self.assertEqual(Preferences(self.preferences.path).get("interfaceLanguage"), "en")
        panel.languages.set_active_id("zh-Hans")
        self.assertEqual(panel.header.get_text(), "Codex 额度 · 演示")
        self.assertIs(self.controller.quota, quota)

    def test_initial_status_icon_renders_and_is_cached(self):
        from gi.repository import GdkPixbuf
        icon = Path(self.panel.indicator.get_icon())
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(icon))
        self.assertEqual((pixbuf.get_width(), pixbuf.get_height()), (24, 24))
        self.assertIn("· 02:34 [演示]", self.panel.indicator.get_label())
        self.assertFalse(self.panel.refresh_button.get_sensitive())
        self.panel.tick()
        self.assertEqual(len(list(icon.parent.iterdir())), 1)

    def test_track_and_hidden_time(self):
        p = self.panel
        p.appearance_buttons["indicatorStyle","track"].clicked()
        full = ET.fromstring(Path(p.indicator.get_icon()).read_text())
        p.part_buttons[2].clicked()
        short = ET.fromstring(Path(p.indicator.get_icon()).read_text())
        self.assertEqual(int(short.get("width")), 24)
        self.assertEqual(int(full.get("width")), 24)
        self.assertIn("H 78", p.indicator.get_label())
        self.assertNotIn("02:34", p.indicator.get_label())
        self.assertEqual(p.reset_value.get_text(),"02:34")
        self.assertEqual(Preferences(self.preferences.path).get("trackParts"),"1")
        p.appearance_buttons["indicatorStyle","ring"].clicked()
        self.assertIn("·", p.indicator.get_label())
        p.part_buttons[1].clicked()
        self.assertTrue(p.part_buttons[1].get_active())
        p.part_buttons[2].clicked()
        self.assertNotIn("·", p.indicator.get_label())
        p.appearance_buttons["indicatorStyle","track"].clicked()
        p.part_buttons[2].clicked()
        p.part_buttons[1].clicked()
        p.part_buttons[2].clicked()
        self.assertEqual(Preferences(self.preferences.path).get("trackParts"), "2")

    def test_buttons_independent_exclusive_and_persisted(self):
        buttons = self.panel.selectors
        buttons["quotaWindow"]["weekly"].clicked()
        self.assertTrue(buttons["quotaWindow"]["weekly"].get_active())
        self.assertFalse(buttons["quotaWindow"]["five_hour"].get_active())
        self.assertIn("02:34", self.panel.indicator.get_label())
        buttons["countdownWindow"]["weekly"].clicked()
        self.assertIn("天", self.panel.indicator.get_label())
        buttons["countdownWindow"]["weekly"].clicked()
        self.assertTrue(buttons["countdownWindow"]["weekly"].get_active())
        buttons["quotaWindow"]["five_hour"].clicked()
        reloaded = Preferences(self.preferences.path)
        self.assertEqual(reloaded.get("quotaWindow"), "five_hour")
        self.assertEqual(reloaded.get("countdownWindow"), "weekly")

    def test_symbolic_loader_keeps_hole_glyphs_and_progress(self):
        self.panel.selectors["quotaWindow"]["weekly"].clicked()
        theme = self.Gtk.IconTheme.new()
        theme.append_search_path(self.panel.icons.name)
        info = theme.lookup_icon(Path(self.panel.indicator.get_icon()).stem, 192,
                                 self.Gtk.IconLookupFlags.FORCE_SIZE)
        pixels, symbolic = info.load_symbolic_for_context(self.panel.header.get_style_context())
        self.assertTrue(symbolic)
        data = pixels.get_pixels()
        def alpha(x, y):
            return data[y * pixels.get_rowstride() + x * 4 + 3]
        self.assertEqual(alpha(96, 32), 0)  # Empty space above the digits.
        self.assertEqual(alpha(96, 12), 255)  # Active top arc.
        self.assertTrue(50 < alpha(180, 96) < 90)  # Dim remaining track.
        self.assertTrue(any(alpha(x, y) > 200 for x in range(56, 136) for y in range(56, 120)))
        self.assertTrue(any(alpha(x, y) > 200 for x in range(72, 120) for y in range(144, 188)))

    def test_weekly_only_and_missing_selected_window(self):
        self.controller.quota = Quota(None, self.controller.quota.weekly, time.time())
        self.panel.tick()
        self.assertFalse(self.panel.sections["five_hour"].get_visible())
        self.assertIn("天", self.panel.indicator.get_label())
        for key in self.panel.selectors:
            self.panel.selectors[key]["five_hour"].clicked()
        self.assertIn("--:--", self.panel.indicator.get_label())
        self.assertIn("<title>H --</title>", Path(self.panel.indicator.get_icon()).read_text())
        self.assertTrue(self.panel.selectors["quotaWindow"]["five_hour"].get_active())

    def test_expired_and_zero_are_distinct(self):
        now = time.time()
        self.controller.quota = Quota(Window(0, now + 60), Window(62, now - 1), now)
        self.panel.selectors["countdownWindow"]["weekly"].clicked()
        self.assertEqual(self.panel.rows["five_hour"][0].get_text(), "0%")
        self.assertTrue(self.panel.rows["five_hour"][1].get_visible())
        self.assertFalse(self.panel.rows["weekly"][1].get_visible())
        self.assertEqual(self.panel.reset_value.get_text(), "待刷新")

    def test_error_clears_data_and_stale_is_marked(self):
        self.controller.demo = False
        now = time.time()
        self.controller.next_poll = now + 60
        self.controller.quota = Quota(None, Window(62, None), now - 181)
        self.panel.tick()
        self.assertIn("!", self.panel.indicator.get_label())
        self.assertIn("数据已过期", self.panel.message.get_text())
        self.controller.quota = None
        self.controller.error = "额度读取失败；请运行 codex login。"
        self.panel.tick()
        self.assertEqual(self.panel.rows["weekly"][0].get_text(), "--")
        self.assertFalse(self.panel.rows["weekly"][1].get_visible())
        self.assertIn("codex login", self.panel.message.get_text())
        self.assertTrue(self.panel.refresh_button.get_sensitive())

    def test_preference_failure_restores_selection(self):
        original = self.panel.selectors["quotaWindow"]["five_hour"]
        with patch.object(self.preferences, "set", side_effect=OSError):
            self.panel.selectors["quotaWindow"]["weekly"].clicked()
        self.assertTrue(original.get_active())
        self.assertIn("无法保存", self.panel.message.get_text())

    def test_refresh_usage_and_startup_actions(self):
        self.controller.next_poll = time.time() + 60
        with patch.object(self.controller, "refresh") as refresh:
            self.panel.refresh()
            refresh.assert_called_once()
        with patch("codex_quota_bar.linux.webbrowser.open") as open_url:
            self.panel.usage()
            open_url.assert_called_once_with("https://chatgpt.com/codex/settings/usage")
        with patch("codex_quota_bar.linux.startup.set_enabled") as setter, \
             patch("codex_quota_bar.linux.startup.is_enabled", return_value=True):
            self.panel.auto.set_active(True)
            setter.assert_called_once_with(True)
            self.assertTrue(self.panel.auto.get_active())

    def test_open_from_menu_and_close(self):
        next(item for item in self.panel.menu.get_children()
             if item.get_label() == "打开额度面板").activate()
        self.assertTrue(self.panel.window.get_visible())
        self.panel.hide()
        self.assertFalse(self.panel.window.get_visible())

    def test_controls_are_available_without_opening_panel(self):
        p = self.panel
        self.assertFalse(p.window.get_visible())
        self.assertTrue(p.menu_info["weekly"].get_visible())
        p.menu_choices["quotaWindow"]["weekly"].activate()
        self.assertEqual(Preferences(self.preferences.path).get("quotaWindow"), "weekly")
        self.assertTrue(p.menu_choices["quotaWindow"]["weekly"].get_active())
        self.assertFalse(p.menu_choices["quotaWindow"]["five_hour"].get_active())
        p.menu_choices["indicatorStyle"]["track"].activate()
        self.assertIn("W 62", p.indicator.get_label())
        p.menu_parts[2].activate()
        self.assertNotIn("02:34", p.indicator.get_label())
        p.menu_parts[1].activate()  # Do not allow hiding the last reading.
        self.assertTrue(p.menu_parts[1].get_active())
        self.assertFalse(p.window.get_visible())

    def test_direct_menu_refresh_and_usage(self):
        self.controller.demo = False
        self.controller.next_poll = time.time() + 60
        self.panel.tick()
        with patch.object(self.controller, "refresh") as refresh:
            self.panel.menu_refresh.activate()
            refresh.assert_called_once()
        with patch("codex_quota_bar.linux.webbrowser.open") as open_url:
            next(item for item in self.panel.menu.get_children()
                 if item.get_label() == "用量页面").activate()
            open_url.assert_called_once_with("https://chatgpt.com/codex/settings/usage")

    def test_direct_menu_language_switch(self):
        self.panel.menu_languages["en"].activate()
        self.assertEqual(self.panel.menu_refresh.get_label(), "Refresh now")
        self.assertTrue(self.panel.menu_languages["en"].get_active())
        self.assertEqual(Preferences(self.preferences.path).get("interfaceLanguage"), "en")
        self.panel.menu_languages["zh-Hans"].activate()
        self.assertEqual(self.panel.menu_refresh.get_label(), "立即刷新")
        self.assertFalse(self.panel.window.get_visible())

    def test_menu_updates_missing_window_and_error(self):
        p = self.panel
        self.controller.quota = Quota(None, self.controller.quota.weekly, time.time())
        p.tick()
        self.assertFalse(p.menu_info["five_hour"].get_visible())
        self.assertIn("62%", p.menu_info["weekly"].get_label())
        self.controller.demo = False
        self.controller.next_poll = time.time() + 60
        self.controller.quota = None
        self.controller.error = "额度读取失败"
        p.tick()
        self.assertNotIn("62%", p.menu_info["weekly"].get_label())
        self.assertIn("额度读取失败", p.menu_info["status"].get_label())

    def test_menu_startup_and_failed_preference_write(self):
        p = self.panel
        with patch("codex_quota_bar.linux.startup.set_enabled") as setter, \
             patch("codex_quota_bar.linux.startup.is_enabled", return_value=not p.auto.get_active()):
            p.menu_auto.activate()
            setter.assert_called_once_with(p.menu_auto.get_active())
            self.assertEqual(p.auto.get_active(), p.menu_auto.get_active())
        with patch.object(self.preferences, "set", side_effect=OSError):
            p.menu_choices["quotaWindow"]["weekly"].activate()
        self.assertTrue(p.menu_choices["quotaWindow"]["five_hour"].get_active())
        self.assertIn("无法保存", p.menu_info["status"].get_label())
