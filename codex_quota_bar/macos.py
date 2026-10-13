import webbrowser

import rumps

from . import __version__, startup
from .client import UsageError


def run(controller, smoke_test=False):
    app = rumps.App("Codex Quota Bar", title="Codex …", quit_button=None)
    rows = [rumps.MenuItem(f"读取中… {i}") for i in range(5)]
    auto = rumps.MenuItem("登录系统时启动")
    auto.state = startup.is_enabled()

    def toggle(sender):
        try:
            startup.set_enabled(not bool(sender.state))
            sender.state = startup.is_enabled()
        except (OSError, UsageError):
            rumps.alert("无法修改开机启动设置", "请检查用户目录权限和 Codex 路径。")

    auto.set_callback(toggle)
    app.menu = [rumps.MenuItem(f"Codex Quota Bar · {__version__}"), None, *rows, None,
                rumps.MenuItem("立即刷新", callback=controller.refresh),
                rumps.MenuItem("打开 Codex 用量页面", callback=lambda _: webbrowser.open("https://chatgpt.com/codex/settings/usage")),
                rumps.MenuItem("登录说明", callback=lambda _: rumps.alert(
                    "使用 ChatGPT 账号登录", "请在终端运行 codex login。完成后点击“立即刷新”。")),
                auto, rumps.MenuItem("退出", callback=lambda _: rumps.quit_application())]

    def update(_):
        app.title, values = controller.tick()
        for item, value in zip(rows, values):
            item.title = value

    timer = rumps.Timer(update, 1)
    timer.start()
    update(None)
    if smoke_test:
        quit_timer = rumps.Timer(lambda _: rumps.quit_application(), 3)
        quit_timer.start()
    app.run()

