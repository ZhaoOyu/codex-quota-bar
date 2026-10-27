import webbrowser

import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppIndicator
from gi.repository import GLib, Gtk

from . import __version__, startup
from .client import UsageError


def run(controller, smoke_test=False):
    initialized, _ = Gtk.init_check()
    if not initialized:
        raise ValueError("无法连接图形桌面；可用 --once 检查额度。")
    indicator = AppIndicator.Indicator.new(
        "codex-quota-bar", "utilities-system-monitor-symbolic",
        AppIndicator.IndicatorCategory.APPLICATION_STATUS)
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    indicator.set_title("Codex Quota Bar")
    menu = Gtk.Menu()
    header = Gtk.MenuItem(label=f"Codex Quota Bar · {__version__}")
    menu.append(header)
    menu.append(Gtk.SeparatorMenuItem())
    rows = []
    for _ in range(5):
        item = Gtk.MenuItem(label="读取中…")
        rows.append(item)
        menu.append(item)
    menu.append(Gtk.SeparatorMenuItem())

    def action(label, callback):
        item = Gtk.MenuItem(label=label)
        item.connect("activate", callback)
        menu.append(item)

    action("立即刷新", controller.refresh)
    action("打开 Codex 用量页面", lambda *_: webbrowser.open("https://chatgpt.com/codex/settings/usage"))
    action("登录说明", lambda *_: show_message("请在终端运行 codex login，选择 ChatGPT 登录。\n完成后点击“立即刷新”。"))
    auto = Gtk.CheckMenuItem(label="登录系统时启动")
    auto.set_active(startup.is_enabled())

    def toggle(item):
        try:
            startup.set_enabled(item.get_active())
        except (OSError, UsageError):
            item.handler_block(toggle_id)
            item.set_active(startup.is_enabled())
            item.handler_unblock(toggle_id)
            show_message("无法修改开机启动设置，请检查用户目录权限和 Codex 路径。")

    toggle_id = auto.connect("toggled", toggle)
    menu.append(auto)
    action("退出", lambda *_: Gtk.main_quit())
    menu.show_all()
    indicator.set_menu(menu)

    def update():
        title, values = controller.tick()
        indicator.set_label(title, title)
        for index, item in enumerate(rows):
            if index < len(values):
                item.set_label(values[index])
                item.show()
            else:
                item.hide()
        return True

    update()
    GLib.timeout_add_seconds(1, update)
    if smoke_test:
        GLib.timeout_add_seconds(3, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()


def show_message(message):
    dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK, text=message)
    dialog.run()
    dialog.destroy()

