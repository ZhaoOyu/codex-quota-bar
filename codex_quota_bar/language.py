"""Language choices for the desktop panels. A preference belongs to one app."""
import locale
import os
import re
import sys

CHOICES = ("system", "zh-Hans", "en")
choice = "system"


def system_language():
    if sys.platform == "darwin":
        from Foundation import NSLocale
        return str(NSLocale.preferredLanguages()[0])
    if sys.platform == "win32":
        import ctypes
        return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "en")
    return (os.environ.get("LANGUAGE") or os.environ.get("LC_ALL") or
            os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en").split(":")[0]


def english():
    language = system_language() if choice == "system" else choice
    return not language.lower().startswith("zh")


def names():
    return ("System default" if english() else "跟随系统", "简体中文", "English")


def select(value):
    global choice
    choice = value if value in CHOICES else "system"


ENGLISH = {
    "Codex CLI 不支持所需命令；请升级 Codex CLI。": "Update Codex CLI to use this command.",
    "Codex 启动遇到目录或执行权限问题；请在终端检查 codex app-server。": "Check the permissions for codex app-server in Terminal.",
    "Codex 或 Node 的架构不兼容；请安装适配这台 Mac 的版本。": "Install a Codex or Node build for your Mac architecture.",
    "Codex 提前退出或连接断开": "Codex exited or disconnected",
    "Codex 路径无效；请检查 --codex 或 CODEX_QUOTA_CODEX_BIN。": "Invalid Codex path. Check --codex or CODEX_QUOTA_CODEX_BIN.",
    "Codex 返回格式异常；请升级 CLI 后重试。": "Unexpected Codex response. Update the CLI and retry.",
    "Codex 额度": "Codex Quota",
    "。": ".",
    "五小时": "5-hour",
    "倒计时": "Countdown",
    "刷新": "Refresh",
    "剩余": " remaining",
    "右侧倒计时": "Countdown",
    "周额度重置：": "Weekly reset: ",
    "图标额度": "Quota window",
    "图标：": "Icon: ",
    "圆环": "Ring",
    "天": "d",
    "小时": "h",
    "待刷新": "Awaiting refresh",
    "打开额度面板": "Open quota panel",
    "找不到 Node.js；请安装 Node 或从已加载 Node 的终端启动。": "Node.js not found. Install Node or launch from a terminal with Node available.",
    "数据已过期，请刷新": "Readings are stale. Click Refresh.",
    "无效时间": "Invalid time",
    "无法保存显示选择，请检查配置目录权限。": "Could not save display preferences. Check folder permissions.",
    "无法修改开机启动设置": "Could not change login startup",
    "无法修改开机启动设置，请检查用户目录权限和 Codex 路径。": "Could not change login startup. Check the home folder permissions and Codex path.",
    "无法启动 Codex CLI；请检查安装和执行权限。": "Could not start Codex CLI. Check the installation and permissions.",
    "显示": "Show",
    "显示内容": "Show in menu bar",
    "更新于": "Updated at",
    "未找到 Codex CLI；请安装并运行 codex login。": "Codex CLI not found. Install it and run codex login.",
    "未提供": "Unavailable",
    "未提供此额度窗口": "Quota window unavailable",
    "未返回 Codex 额度；请确认使用 ChatGPT 账号登录。": "No Codex quota returned. Check your ChatGPT login.",
    "正在刷新额度…": "Updating quota…",
    "正在读取 Codex 额度…": "Reading Codex quota…",
    "正在读取…": "Reading…",
    "每 60 秒刷新": "Refreshes every 60 seconds",
    "每周": "Weekly",
    "演示": "Demo",
    "演示数据": "Demo data",
    "演示数据 · 不连接账户": "Demo data · Offline",
    "用量页面": "Usage page",
    "登录系统时启动": "Open at login",
    "立即刷新": "Refresh now",
    "等待数据…": "Waiting for data…",
    "结束：": " ends: ",
    "菜单栏剩余时间": "Menu bar countdown",
    "菜单栏样式": "Menu bar style",
    "请检查用户目录权限和 Codex 路径。": "Check your home folder permissions and Codex path.",
    "读取异常；请检查 Codex 安装，稍后自动重试。": "Read failed. Check your Codex installation. Retrying shortly.",
    "读取超时；请检查网络，稍后自动重试。": "Read timed out. Check the network. Retrying shortly.",
    "账号未返回五小时或周额度；当前套餐可能使用其他计费窗口。": "No five-hour or weekly quota was returned for this plan.",
    "跑道": "Track",
    "距离重置": "Time until reset",
    "退出": "Quit",
    "重置": " reset",
    "重置于": "Resets at",
    "重置倒计时": " reset countdown",
    "隐藏": "Hide",
    "额度": " quota",
    "额度剩余": " quota remaining",
    "额度数值": "Quota value",
    "额度读取失败；请运行 codex login，以 ChatGPT 账号登录后重试。": "Could not read quota. Run codex login with your ChatGPT account.",
    "（": " (",
    "（退出码": " (exit code",
    "）": ")",
    "，": ", ",
    "：": ": ",
    "；": "; ",
    "；请在终端运行 codex app-server 检查启动错误。": ". Run codex app-server in Terminal for details."
}
_fragments = re.compile("|".join(re.escape(k) for k in sorted(ENGLISH, key=len, reverse=True)))


def tr(text):
    if not text or not english():
        return text
    if text in ENGLISH:
        return ENGLISH[text]
    return _fragments.sub(lambda m: ENGLISH[m.group()], text)
