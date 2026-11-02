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
