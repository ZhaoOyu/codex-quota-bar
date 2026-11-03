"""Shared desktop display rules, independent of AppKit and GTK."""

WINDOWS = ("five_hour", "weekly")
WINDOW_LABELS = {"five_hour": "五小时", "weekly": "每周"}
CONTROL_LABELS = {"quotaWindow": "图标额度", "countdownWindow": "右侧倒计时"}


def fraction(window, now):
    if window is None or (window.resets_at is not None and now >= window.resets_at):
        return None
    return max(0, min(1, window.remaining / 100))


def choose_window(saved, quota):
    if saved in WINDOWS:
        return saved
    return "five_hour" if quota and quota.five_hour is not None else "weekly"

# First option is also the default for existing installations.
APPEARANCE = {
    "indicatorStyle": ("菜单栏样式", {"ring": "圆环", "track": "跑道"}),
    "timeDisplay": ("菜单栏剩余时间", {"shown": "显示", "hidden": "隐藏"}),
}


def appearance(key, value):
    options = APPEARANCE[key][1]
    return value if value in options else next(iter(options))


def track_reading(window, now, choice, time_text):
    marker = "H" if choice == "five_hour" else "W"
    value = "--" if fraction(window, now) is None else str(int(window.remaining))
    return f"{marker} {value}" + (f" · {time_text}" if time_text else "")
