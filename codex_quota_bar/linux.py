"""Native GTK quota panel and AppIndicator symbolic ring."""
from . import language
from .language import tr

import hashlib
from pathlib import Path
import tempfile
import time
import webbrowser

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppIndicator
from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo

from . import __version__, startup
from .client import UsageError
from .display import APPEARANCE, appearance, track_reading, CONTROL_LABELS, WINDOW_LABELS, choose_window, fraction
from .linux_display import Preferences, status_svg, track_svg
from .model import countdown, remaining_text, reset_text


def text_outline(text, center, baseline, size):
    """Convert native font glyphs to paths so GTK can recolor symbolic text."""
    context = cairo.Context(cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None))
    context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    context.set_font_size(size)
    bounds = context.text_extents(text)
    context.move_to(center - bounds.x_bearing - bounds.width / 2, baseline)
    context.text_path(text)
    commands = {cairo.PATH_MOVE_TO: "M", cairo.PATH_LINE_TO: "L",
                cairo.PATH_CURVE_TO: "C", cairo.PATH_CLOSE_PATH: "Z"}
    path = " ".join(commands[kind] + " ".join(f"{number:.4f}" for number in points)
                    for kind, points in context.copy_path())
    return f'<path d="{path}"/>'


def track_text_layout(reading):
    # Match librsvg's Pango text shaping, including CJK font fallback. Cairo's
    # toy font metrics can disagree with the glyphs used in the final SVG.
    layout = Pango.Layout.new(PangoCairo.FontMap.get_default().create_context())
    font = Pango.FontDescription("sans-serif bold")
    font.set_absolute_size(11 * Pango.SCALE)
    layout.set_font_description(font)
    layout.set_text(reading, -1)
    return layout


def track_icon(reading, value):
    layout = track_text_layout(reading)
    _, logical = layout.get_pixel_extents()
    baseline = (24 - logical.height) / 2 - logical.y + layout.get_baseline() / Pango.SCALE
    # Always take the wide-image branch, even for short/unknown readings.
    return track_svg(reading, value, max(40, logical.width + 24), baseline)


class QuotaPanel:
    def __init__(self, controller, preferences=None, *, indicator_id="codex-quota-bar"):
        self.controller = controller
        self.preferences = preferences if preferences is not None else Preferences()
        language.select(self.preferences.get("interfaceLanguage"))
        self.preference_error = ""
        self.icons = tempfile.TemporaryDirectory(prefix="codex-quota-icons-")
        self.icon_key = None
        self.icon_paths = []
        self.panel_size = None
        self.window = Gtk.Window(title=tr("Codex 额度"))
        self.window.set_name("codex-quota")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.set_keep_above(True)
        self.window.connect("delete-event", self.hide)
        self.window.connect("focus-out-event", self.hide)
        self.window.connect("key-press-event", self.key_pressed)
        self.css = Gtk.CssProvider()
        self.css.load_from_data(b"""
            #codex-quota .heading { font-size: 16px; font-weight: bold; }
            #codex-quota .row-title { font-size: 14px; font-weight: bold; }
            #codex-quota .value { font-size: 16px; font-weight: bold; }
            #codex-quota .detail { font-size: 11px; }
            #codex-quota button { padding: 4px 8px; min-height: 22px; }
            #codex-quota progressbar trough { min-height: 6px; }
            #codex-quota progressbar progress { min-height: 6px; }
        """)
        Gtk.StyleContext.add_provider_for_screen(self.window.get_screen(), self.css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.IconTheme.get_default().append_search_path(str(Path(__file__).with_name("icons")))
        self.build()
        self.indicator = AppIndicator.Indicator.new(
            indicator_id, "utilities-system-monitor-symbolic",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title("Codex Quota Bar")
        self.indicator.set_icon_theme_path(self.icons.name)
        self.build_menu()
        # AppIndicator hosts own primary-click behavior. Export real menu items
        # so GNOME/Wayland can display controls directly, without a second click.
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.tick()

    def build_menu(self):
        old_menu = getattr(self, "menu", None)
        self.menu = Gtk.Menu()
        self.menu_info = {}
        for key in ("five_hour", "weekly", "reset", "status"):
            self.menu_info[key] = self.menu_action("", lambda *_: None)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu_refresh = self.menu_action("立即刷新", self.refresh)
        self.menu_choices = {}
        groups = [(key, title, WINDOW_LABELS) for key, title in CONTROL_LABELS.items()]
        groups.append(("indicatorStyle", APPEARANCE["indicatorStyle"][0],
                       APPEARANCE["indicatorStyle"][1]))
        for key, title, options in groups:
            parent = self.menu_action(title, lambda *_: None)
            submenu = Gtk.Menu()
            parent.set_submenu(submenu)
            self.menu_choices[key] = {}
            for choice, label in options.items():
                item = Gtk.CheckMenuItem(label=tr(label))
                item.set_draw_as_radio(True)
                item.connect("activate", self.select, key, choice)
                submenu.append(item)
                self.menu_choices[key][choice] = item
        self.menu_parts = {}
        for bit, label in ((1, "额度数值"), (2, "倒计时")):
            item = Gtk.CheckMenuItem(label=tr(label))
            item.connect("activate", self.toggle_part, bit)
            self.menu.append(item)
            self.menu_parts[bit] = item
        self.menu_auto = Gtk.CheckMenuItem(label=tr("登录系统时启动"))
        self.menu_auto.connect("activate", self.menu_toggle_startup)
        self.menu.append(self.menu_auto)
        parent = self.menu_action("Language" if language.english() else "语言", lambda *_: None)
        submenu = Gtk.Menu()
        parent.set_submenu(submenu)
        self.menu_languages = {}
        for choice, label in zip(language.CHOICES, language.names()):
            item = Gtk.CheckMenuItem(label=label)
            item.set_draw_as_radio(True)
            item.connect("activate", self.menu_change_language, choice)
            submenu.append(item)
            self.menu_languages[choice] = item
        self.menu_action("用量页面", self.usage)
        open_item = self.menu_action("打开额度面板", self.present)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu_action("退出", lambda *_: Gtk.main_quit())
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        self.indicator.set_secondary_activate_target(open_item)
        if old_menu is not None:
            old_menu.destroy()

    @staticmethod
    def checked(item, active, callback):
        item.handler_block_by_func(callback)
        item.set_active(active)
        item.handler_unblock_by_func(callback)

    def menu_toggle_startup(self, item):
        self.auto.set_active(item.get_active())
        self.tick()

    def menu_change_language(self, _, choice):
        self.languages.set_active_id(choice)
        self.tick()

    def update_menu(self, quota, quota_choice, time_choice, style, parts):
        for key in ("five_hour", "weekly"):
            item = self.menu_info[key]
            item.set_visible(key == "weekly" or bool(quota and quota.five_hour is not None))
            value, _, detail = self.rows[key]
            item.set_label(tr(WINDOW_LABELS[key] + "额度剩余") + ": " + value.get_text()
                           + " · " + detail.get_text())
        self.menu_info["reset"].set_label(self.reset_title.get_text() + ": " + self.reset_value.get_text())
        self.menu_info["status"].set_label(self.message.get_text())
        self.menu_refresh.set_sensitive(self.refresh_button.get_sensitive())
        for key, selection in (("quotaWindow", quota_choice), ("countdownWindow", time_choice),
                               ("indicatorStyle", style)):
            for choice, item in self.menu_choices[key].items():
                self.checked(item, choice == selection, self.select)
        for bit, item in self.menu_parts.items():
            self.checked(item, bool(parts & bit), self.toggle_part)
            item.set_sensitive(style == "track" or bit == 2)
        self.checked(self.menu_auto, self.auto.get_active(), self.menu_toggle_startup)
        for choice, item in self.menu_languages.items():
            self.checked(item, choice == language.choice, self.menu_change_language)

    def menu_action(self, title, callback):
        item = Gtk.MenuItem(label=tr(title))
        item.connect("activate", callback)
        self.menu.append(item)
        return item

    def label(self, title="", style=None, right=False):
        label = Gtk.Label(label=tr(title), xalign=1 if right else 0)
        label.set_valign(Gtk.Align.CENTER)
        if style:
            label.get_style_context().add_class(style)
        return label

    def row(self, icon, title, value=None, heading=False):
        box = Gtk.Box(spacing=14)
        glyph = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        glyph.set_pixel_size(22)
        glyph.set_valign(Gtk.Align.CENTER)
        box.pack_start(glyph, False, False, 0)
        label = self.label(title, "heading" if heading else "row-title")
        box.pack_start(label, True, True, 0)
        if value is not None:
            box.pack_end(value, False, False, 0)
        return box, label

    def build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_border_width(18)
        root.set_size_request(360, -1)
        self.window.add(root)
        header, self.header = self.row("codex-gauge-symbolic", "Codex 额度", heading=True)
        header.set_size_request(-1, 30)
        root.pack_start(header, False, False, 0)
        root.pack_start(Gtk.Separator(), False, False, 0)
        self.rows = {}
        self.sections = {}
        for key, icon in (("five_hour", "preferences-system-time-symbolic"),
                          ("weekly", "x-office-calendar-symbolic")):
            section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
            value = self.label("--", "value", right=True)
            row, _ = self.row(icon, WINDOW_LABELS[key] + "额度剩余", value)
            section.pack_start(row, False, False, 0)
            bar = Gtk.ProgressBar()
            bar.set_margin_start(36)
            bar.get_accessible().set_name(tr(WINDOW_LABELS[key] + "额度剩余"))
            section.pack_start(bar, False, False, 0)
            detail = self.label("等待数据…", "detail")
            detail.get_style_context().add_class("dim-label")
            detail.set_margin_start(36)
            section.pack_start(detail, False, False, 0)
            root.pack_start(section, False, False, 0)
            self.rows[key] = (value, bar, detail)
            self.sections[key] = section
        root.pack_start(Gtk.Separator(), False, False, 0)
        self.reset_value = self.label("--:--", "value", right=True)
        reset_row, self.reset_title = self.row("codex-hourglass-symbolic", "距离重置", self.reset_value)
        reset_row.set_size_request(-1, 32)
        root.pack_start(reset_row, False, False, 0)
        root.pack_start(Gtk.Separator(), False, False, 0)
        self.selectors = {}
        for key, title in CONTROL_LABELS.items():
            row = Gtk.Box(spacing=6)
            row.pack_start(self.label(title), True, True, 0)
            self.selectors[key] = {}
            for choice in ("weekly", "five_hour"):
                button = Gtk.ToggleButton(label=tr(WINDOW_LABELS[choice]))
                button.set_size_request(72, 30)
                button.get_accessible().set_name(tr(title + "：" + WINDOW_LABELS[choice]))
                button.connect("clicked", self.select, key, choice)
                row.pack_start(button, False, False, 0)
                self.selectors[key][choice] = button
            root.pack_start(row, False, False, 0)
        self.appearance_buttons = {}
        for key, (label, options) in APPEARANCE.items():
            if key == "timeDisplay":
                continue
            row = Gtk.Box(spacing=6)
            row.pack_start(self.label(label), True, True, 0)
            for choice, title in options.items():
                button = Gtk.ToggleButton(label=tr(title))
                button.set_size_request(72, 30)
                button.get_accessible().set_name(tr(label+"："+title))
                button.connect("clicked",self.select,key,choice)
                row.pack_start(button,False,False,0)
                self.appearance_buttons[key,choice] = button
            root.pack_start(row,False,False,0)
        row = Gtk.Box(spacing=6)
        row.pack_start(self.label("显示内容"), True, True, 0)
        self.part_buttons = {}
        for bit, label in ((1, "额度数值"), (2, "倒计时")):
            button = Gtk.ToggleButton(label=tr(label))
            button.get_accessible().set_name(tr(label))
            button.set_size_request(72, 30)
            button.connect("clicked", self.toggle_part, bit)
            row.pack_start(button, False, False, 0)
            self.part_buttons[bit] = button
        root.pack_start(row, False, False, 0)
        self.message = self.label("正在读取…", "detail")
        self.message.get_style_context().add_class("dim-label")
        self.message.set_line_wrap(True)
        self.message.set_max_width_chars(40)
        self.message.set_size_request(-1, 34)
        root.pack_start(self.message, False, False, 0)
        actions = Gtk.Box(spacing=6, homogeneous=True)
        for title, callback in (("刷新", self.refresh), ("用量页面", self.usage),
                                ("退出", lambda *_: Gtk.main_quit())):
            button = Gtk.Button(label=tr(title))
            button.connect("clicked", callback)
            actions.pack_start(button, True, True, 0)
            if title == "刷新":
                self.refresh_button = button
        root.pack_start(actions, False, False, 0)
        root.pack_start(self.language_row(), False, False, 0)
        footer = Gtk.Box()
        self.auto = Gtk.CheckButton(label=tr("登录系统时启动"))
        self.auto.set_active(startup.is_enabled())
        self.auto_handler = self.auto.connect("toggled", self.toggle_startup)
        footer.pack_start(self.auto, True, True, 0)
        version = self.label("v" + __version__, "detail", right=True)
        version.get_style_context().add_class("dim-label")
        footer.pack_end(version, False, False, 0)
        root.pack_start(footer, False, False, 0)
        root.show_all()

    def tick(self):
        title, details = self.controller.tick()
        now, quota = time.time(), self.controller.quota
        quota_choice = choose_window(self.preferences.get("quotaWindow"), quota)
        time_choice = choose_window(self.preferences.get("countdownWindow"), quota)
        quota_window = getattr(quota, quota_choice) if quota else None
        time_window = getattr(quota, time_choice) if quota else None
        for key, selection in (("quotaWindow", quota_choice), ("countdownWindow", time_choice)):
            for choice, button in self.selectors[key].items():
                # GtkToggleButton.set_active emits clicked; block our choice callback.
                button.handler_block_by_func(self.select)
                button.set_active(choice == selection)
                button.handler_unblock_by_func(self.select)
        style = appearance("indicatorStyle", self.preferences.get("indicatorStyle"))
        parts = self.visible_parts(style)
        show_time = bool(parts & 2)
        for (name, choice), button in self.appearance_buttons.items():
            button.handler_block_by_func(self.select)
            button.set_active(choice == appearance(name, self.preferences.get(name)))
            button.handler_unblock_by_func(self.select)
        time_text = tr(countdown(time_window, now, show_days=time_choice == "weekly"))
        amount = track_reading(quota_window, now, quota_choice, "")
        for bit, button in self.part_buttons.items():
            button.handler_block_by_func(self.toggle_part)
            button.set_active(bool(parts & bit))
            button.set_label(tr(amount if bit == 1 else time_text))
            button.handler_unblock_by_func(self.toggle_part)
        if style == "track":
            reading = " · ".join(text for bit, text in ((1, amount), (2, time_text)) if parts & bit)
            svg = track_icon(reading, fraction(quota_window, now))
            reading = ""  # The reading is inside the track, not a second label.
        else:
            reading = ("· " + time_text) if show_time else ""
            svg = status_svg(quota_window, now, quota_choice, text_outline)
        key = hashlib.sha256(svg.encode()).hexdigest()[:16]
        if key != self.icon_key:
            suffix = "-symbolic" if style == "ring" else ""
            path = Path(self.icons.name) / f"quota-{key}{suffix}.svg"
            path.write_text(svg)
            self.indicator.set_icon_full(str(path), tr("Codex 额度：" + WINDOW_LABELS[quota_choice]
                                         + "剩余 " + remaining_text(quota_window, now)))
            self.icon_key = key
            if path in self.icon_paths:
                self.icon_paths.remove(path)
            self.icon_paths.append(path)
            if len(self.icon_paths) > 64:
                self.icon_paths.pop(0).unlink(missing_ok=True)
        warning = bool(self.controller.error) or bool(quota and now - quota.fetched_at > 180)
        self.indicator.set_label(tr(" ".join(x for x in (
                                 "!" if warning else "", reading,
                                 "[演示]" if self.controller.demo else "") if x)), "")
        self.indicator.set_title(tr("Codex 额度 · " + title))
        self.header.set_text(tr("Codex 额度 · 演示" if self.controller.demo else "Codex 额度"))
        self.sections["five_hour"].set_visible(bool(quota and quota.five_hour is not None))
        for name, (value, bar, detail) in self.rows.items():
            window = getattr(quota, name) if quota else None
            value.set_text(tr(remaining_text(window, now)))
            amount = fraction(window, now)
            bar.set_visible(amount is not None)
            bar.set_fraction(amount if amount is not None else 0)
            detail.set_text(tr("重置于 " + reset_text(window) if window else "未提供此额度窗口"))
        self.reset_title.set_text(tr(WINDOW_LABELS[time_choice] + "重置倒计时"))
        self.reset_value.set_text(tr(time_text))
        message = self.preference_error or ("演示数据 · 不连接账户" if self.controller.demo else
                   "正在刷新额度…" if self.controller.busy else details[-1])
        self.message.set_text(tr(message))
        self.message.set_tooltip_text(tr(message))
        self.refresh_button.set_sensitive(not self.controller.busy and not self.controller.demo)
        self.update_menu(quota, quota_choice, time_choice, style, parts)
        # Shrink when a section disappears, without requesting a 1px native window.
        _, natural = self.window.get_child().get_preferred_size()
        size = (natural.width, natural.height)
        if size != self.panel_size:
            self.window.resize(*size)
            self.panel_size = size
        return True

    def language_row(self):
        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label=tr("Language" if language.english() else "语言"), xalign=0), True, True, 0)
        combo = self.languages = Gtk.ComboBoxText()
        for key, name in zip(language.CHOICES, language.names()):
            combo.append(key, name)
        combo.set_active_id(language.choice)
        combo.connect("changed", self.change_language)
        row.pack_end(combo, False, False, 0)
        return row

    def change_language(self, combo):
        value = combo.get_active_id()
        try:
            self.preferences.set("interfaceLanguage", value)
        except OSError:
            self.preference_error = "无法保存显示选择，请检查配置目录权限。"
            self.tick()
            return
        language.select(value)
        self.window.get_child().destroy()
        self.window.set_title(tr("Codex 额度"))
        self.build()
        self.indicator.set_secondary_activate_target(None)
        self.build_menu()
        self.tick()

    def visible_parts(self, style):
        ring = 1 if self.preferences.get("timeDisplay") == "hidden" else 3
        if style == "track":
            return int(self.preferences.get("trackParts") or ring)
        return ring

    def toggle_part(self, sender, bit):
        style = appearance("indicatorStyle", self.preferences.get("indicatorStyle"))
        next_parts = self.visible_parts(style) ^ bit
        if style == "ring" and bit == 2:
            if self.preferences.get("trackParts") is None:
                try:
                    self.preferences.set("trackParts", str(self.visible_parts("track")))
                except OSError:
                    self.preference_error = "无法保存显示选择，请检查配置目录权限。"
                    self.tick()
                    return
            self.select(sender, "timeDisplay", "shown" if next_parts & 2 else "hidden")
        elif style == "track" and next_parts:
            self.select(sender, "trackParts", str(next_parts))
        else:
            self.tick()

    def select(self, _, key, choice):
        try:
            self.preferences.set(key, choice)
            self.preference_error = ""
        except OSError:
            self.preference_error = "无法保存显示选择，请检查配置目录权限。"
        self.tick()

    def refresh(self, *_):
        self.controller.refresh()
        self.tick()

    def usage(self, *_):
        webbrowser.open("https://chatgpt.com/codex/settings/usage")

    def toggle_startup(self, button):
        try:
            startup.set_enabled(button.get_active())
        except (OSError, UsageError):
            show_message(tr("无法修改开机启动设置，请检查用户目录权限和 Codex 路径。"), self.window)
        button.handler_block(self.auto_handler)
        button.set_active(startup.is_enabled())
        button.handler_unblock(self.auto_handler)

    def present(self, *_):
        self.tick()
        self.window.show()
        # On X11 place near the panel pointer; Wayland controls window placement.
        display = self.window.get_display()
        pointer = display.get_default_seat().get_pointer()
        _, x, y = pointer.get_position()
        monitor = display.get_monitor_at_point(x, y)
        if monitor:
            area = monitor.get_workarea()
            width, height = self.window.get_size()
            left = max(area.x, min(x - width // 2, area.x + area.width - width))
            top = area.y + 8 if y < area.y + area.height // 2 else area.y + area.height - height - 8
            self.window.move(left, max(area.y, top))
        self.window.present()

    def hide(self, *_):
        self.window.hide()
        return True

    def key_pressed(self, _, event):
        return self.hide() if event.keyval == Gdk.KEY_Escape else False

    def close(self):
        self.indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
        self.window.destroy()
        self.menu.destroy()
        Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), self.css)
        self.icons.cleanup()


def run(controller, smoke_test=False):
    initialized, _ = Gtk.init_check()
    if not initialized:
        raise ValueError("无法连接图形桌面；可用 --once 检查额度。")
    panel = QuotaPanel(controller)
    timer = GLib.timeout_add_seconds(1, panel.tick)
    if smoke_test:
        panel.present()
        GLib.timeout_add_seconds(3, lambda: (Gtk.main_quit(), False)[1])
    try:
        Gtk.main()
    finally:
        GLib.source_remove(timer)
        panel.close()


def show_message(message, parent=None):
    dialog = Gtk.MessageDialog(transient_for=parent, modal=True,
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK, text=tr(message))
    dialog.run()
    dialog.destroy()
