"""Native GTK quota panel and AppIndicator symbolic ring."""

import hashlib
from pathlib import Path
import tempfile
import time
import webbrowser

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppIndicator
from gi.repository import Gdk, GLib, GObject, Gtk

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


class QuotaPanel:
    def __init__(self, controller, preferences=None, *, indicator_id="codex-quota-bar"):
        self.controller = controller
        self.preferences = preferences if preferences is not None else Preferences()
        self.preference_error = ""
        self.icons = tempfile.TemporaryDirectory(prefix="codex-quota-icons-")
        self.icon_key = None
        self.icon_paths = []
        self.panel_size = None
        self.window = Gtk.Window(title="Codex 额度")
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
        self.menu = Gtk.Menu()
        open_item = self.menu_action("打开额度面板", self.present)
        self.menu_action("立即刷新", self.refresh)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu_action("退出", lambda *_: Gtk.main_quit())
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        self.indicator.set_secondary_activate_target(open_item)
        # Newer Ayatana versions can forward primary activation directly.
        if GObject.signal_lookup("activate", self.indicator.__gtype__):
            self.indicator.connect("activate", self.present)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.tick()

    def menu_action(self, title, callback):
        item = Gtk.MenuItem(label=title)
        item.connect("activate", callback)
        self.menu.append(item)
        return item

    def label(self, title="", style=None, right=False):
        label = Gtk.Label(label=title, xalign=1 if right else 0)
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
            bar.get_accessible().set_name(WINDOW_LABELS[key] + "额度剩余")
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
                button = Gtk.ToggleButton(label=WINDOW_LABELS[choice])
                button.set_size_request(72, 30)
                button.get_accessible().set_name(title + "：" + WINDOW_LABELS[choice])
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
                button = Gtk.ToggleButton(label=title)
                button.set_size_request(72, 30)
                button.get_accessible().set_name(label+"："+title)
                button.connect("clicked",self.select,key,choice)
                row.pack_start(button,False,False,0)
                self.appearance_buttons[key,choice] = button
            root.pack_start(row,False,False,0)
        row = Gtk.Box(spacing=6)
        row.pack_start(self.label("显示内容"), True, True, 0)
        self.part_buttons = {}
        for bit, label in ((1, "额度数值"), (2, "倒计时")):
            button = Gtk.ToggleButton(label=label)
            button.get_accessible().set_name(label)
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
            button = Gtk.Button(label=title)
            button.connect("clicked", callback)
            actions.pack_start(button, True, True, 0)
            if title == "刷新":
                self.refresh_button = button
        root.pack_start(actions, False, False, 0)
        footer = Gtk.Box()
        self.auto = Gtk.CheckButton(label="登录系统时启动")
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
        time_text = countdown(time_window, now, show_days=time_choice == "weekly")
        amount = track_reading(quota_window, now, quota_choice, "")
        for bit, button in self.part_buttons.items():
            button.handler_block_by_func(self.toggle_part)
            button.set_active(bool(parts & bit))
            button.set_label(amount if bit == 1 else time_text)
            button.handler_unblock_by_func(self.toggle_part)
        if style == "track":
            reading = " · ".join(text for bit, text in ((1, amount), (2, time_text)) if parts & bit)
            metric = cairo.Context(cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None))
            metric.select_font_face("sans-serif",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
            metric.set_font_size(11)
            svg = track_svg(reading,fraction(quota_window,now),max(34,int(metric.text_extents(reading).width+19)),text_outline)
        else:
            svg = status_svg(quota_window, now, quota_choice, text_outline)
        key = hashlib.sha256(svg.encode()).hexdigest()[:16]
        if key != self.icon_key:
            path = Path(self.icons.name) / f"quota-{key}-symbolic.svg"
            path.write_text(svg)
            self.indicator.set_icon_full(str(path), "Codex 额度：" + WINDOW_LABELS[quota_choice]
                                         + "剩余 " + remaining_text(quota_window, now))
            self.icon_key = key
            if path in self.icon_paths:
                self.icon_paths.remove(path)
            self.icon_paths.append(path)
            if len(self.icon_paths) > 64:
                self.icon_paths.pop(0).unlink(missing_ok=True)
        warning = bool(self.controller.error) or bool(quota and now - quota.fetched_at > 180)
        self.indicator.set_label(" ".join(x for x in ("·" if show_time and style=="ring" else "",
                                 "!" if warning else "", time_text if show_time and style=="ring" else "",
                                 "[演示]" if self.controller.demo else "") if x), "")
        self.indicator.set_title("Codex 额度 · " + title)
        self.header.set_text("Codex 额度 · 演示" if self.controller.demo else "Codex 额度")
        self.sections["five_hour"].set_visible(bool(quota and quota.five_hour is not None))
        for name, (value, bar, detail) in self.rows.items():
            window = getattr(quota, name) if quota else None
            value.set_text(remaining_text(window, now))
            amount = fraction(window, now)
            bar.set_visible(amount is not None)
            bar.set_fraction(amount if amount is not None else 0)
            detail.set_text("重置于 " + reset_text(window) if window else "未提供此额度窗口")
        self.reset_title.set_text(WINDOW_LABELS[time_choice] + "重置倒计时")
        self.reset_value.set_text(time_text)
        message = self.preference_error or ("演示数据 · 不连接账户" if self.controller.demo else
                   "正在刷新额度…" if self.controller.busy else details[-1])
        self.message.set_text(message)
        self.message.set_tooltip_text(message)
        self.refresh_button.set_sensitive(not self.controller.busy and not self.controller.demo)
        self.menu.get_children()[1].set_sensitive(self.refresh_button.get_sensitive())
        # Shrink when a section disappears, without requesting a 1px native window.
        _, natural = self.window.get_child().get_preferred_size()
        size = (natural.width, natural.height)
        if size != self.panel_size:
            self.window.resize(*size)
            self.panel_size = size
        return True

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
            show_message("无法修改开机启动设置，请检查用户目录权限和 Codex 路径。", self.window)
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
                               buttons=Gtk.ButtonsType.OK, text=message)
    dialog.run()
    dialog.destroy()
