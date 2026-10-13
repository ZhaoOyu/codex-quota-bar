"""Pure quota parsing and presentation; never infer a reset from elapsed time."""

from dataclasses import dataclass
from datetime import datetime
import math


@dataclass(frozen=True)
class Window:
    remaining: float
    resets_at: float | None


@dataclass(frozen=True)
class Quota:
    five_hour: Window | None
    weekly: Window | None
    fetched_at: float
    plan: str = ""


def number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def parse_quota(result: dict, now: float) -> Quota:
    buckets = result.get("rateLimitsByLimitId")
    if isinstance(buckets, dict) and "codex" in buckets:
        bucket = buckets["codex"]
    else:
        bucket = result.get("rateLimits")
    if not isinstance(bucket, dict) or bucket.get("limitId") not in (None, "codex"):
        raise ValueError("未返回 Codex 额度；请确认使用 ChatGPT 账号登录。")
    windows = {}
    for key in ("primary", "secondary"):
        raw = bucket.get(key)
        if not isinstance(raw, dict):
            continue
        duration = raw.get("windowDurationMins")
        used = raw.get("usedPercent")
        # Match actual durations, not primary/secondary position or plan names.
        if not number(duration) or duration not in (300, 10080) or not number(used):
            continue
        reset = raw.get("resetsAt")
        windows[duration] = Window(max(0, min(100, 100 - used)),
                                   reset if number(reset) and reset > 0 else None)
    if not windows:
        raise ValueError("账号未返回五小时或周额度；当前套餐可能使用其他计费窗口。")
    plan = bucket.get("planType")
    return Quota(windows.get(300), windows.get(10080), now,
                 plan if isinstance(plan, str) else "")


def remaining_text(window: Window | None, now: float) -> str:
    if window is None:
        return "--"
    if window.resets_at is not None and now >= window.resets_at:
        return "待刷新"
    # Floor avoids displaying 100% for partially consumed quotas.
    return f"{math.floor(window.remaining)}%"


def countdown(window: Window | None, now: float) -> str:
    if window is None or window.resets_at is None:
        return "--:--"
    seconds = window.resets_at - now
    if seconds <= 0:
        return "待刷新"
    minutes = math.ceil(seconds / 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def reset_text(window: Window | None) -> str:
    if window is None or window.resets_at is None:
        return "未提供"
    try:
        return datetime.fromtimestamp(window.resets_at).astimezone().strftime("%m-%d %H:%M:%S %Z")
    except (ValueError, OverflowError, OSError):
        return "无效时间"


def present(quota: Quota | None, now: float, error: str = "", demo=False):
    stale = bool(error) or (quota is not None and now - quota.fetched_at > 180)
    prefix = "[演示] " if demo else ""
    if quota is None:
        return prefix + ("Codex !" if error else "Codex …"), [
            "五小时剩余：--", "每周剩余：--", "五小时结束：--", "周额度重置：--",
            error or "正在读取 Codex 额度…"]
    title = (f"5h {remaining_text(quota.five_hour, now)} · "
             f"W {remaining_text(quota.weekly, now)} · {countdown(quota.five_hour, now)}")
    updated = datetime.fromtimestamp(quota.fetched_at).strftime("%H:%M:%S")
    status = error or ("数据已过期，请刷新" if stale else f"更新于 {updated} · 每 60 秒刷新")
    return prefix + ("! " if stale else "") + title, [
        f"五小时剩余：{remaining_text(quota.five_hour, now)}",
        f"每周剩余：{remaining_text(quota.weekly, now)}",
        f"五小时结束：{reset_text(quota.five_hour)}",
        f"周额度重置：{reset_text(quota.weekly)}", status]

