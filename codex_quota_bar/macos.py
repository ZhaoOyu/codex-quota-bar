"""Native AppKit status icon and transient, system-material quota popover."""

import time
import webbrowser

import AppKit as A
import objc
from Foundation import NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes, NSUserDefaults, NSAttributedString

from . import __version__, startup
from .client import UsageError
from .model import countdown, remaining_text, reset_text


def symbol(name, description):
    return A.NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, description)


def fraction(window, now):
    # Missing and expired windows must not look like a measured zero or 100%.
    if window is None or (window.resets_at is not None and now >= window.resets_at):
        return None
    return max(0, min(1, window.remaining / 100))


WINDOWS = ("five_hour", "weekly")
WINDOW_LABELS = {"five_hour": "五小时", "weekly": "每周"}
CONTROL_LABELS = {"quotaWindow": "图标额度", "countdownWindow": "右侧倒计时"}


def selected_window(preferences, key, quota):
    selected = preferences.stringForKey_(key)
    if selected in WINDOWS:
        return selected
    # Before the first explicit choice, use whichever window is available.
    return "five_hour" if quota and quota.five_hour is not None else "weekly"


def status_image(window, now, choice="five_hour"):
    """Larger quota ring completed by a bottom H/W marker and a middle dot."""
    image = A.NSImage.alloc().initWithSize_((35, 24))
    image.lockFocus()
    try:
        value = fraction(window, now)
        # Leave only the letter-sized bottom gap; round caps meet the H/W edges.
        gap = 44 if choice == "five_hour" else 56
        arc = 360 - gap
        for alpha, sweep in ((0.28, arc), (1.0, arc * value if value is not None else 0)):
            if sweep <= 0:
                continue
            A.NSColor.blackColor().colorWithAlphaComponent_(alpha).setStroke()
            path = A.NSBezierPath.bezierPath()
            path.setLineWidth_(2.4)
            path.setLineCapStyle_(A.NSRoundLineCapStyle)
            if value is None:
                path.setLineDash_count_phase_([1, 3], 2, 0)
            path.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                (14, 12), 10.7, 270 - gap / 2, 270 - gap / 2 - sweep, True)
            path.stroke()
        text = remaining_text(window, now).removesuffix("%") if value is not None else "--"
        label = NSAttributedString.alloc().initWithString_attributes_(text, {
            A.NSFontAttributeName: A.NSFont.monospacedDigitSystemFontOfSize_weight_(9 if len(text) > 2 else 10.5, A.NSFontWeightBold),
            A.NSForegroundColorAttributeName: A.NSColor.blackColor(),
        })
        label.drawAtPoint_((14 - label.size().width / 2, 7))
        marker = NSAttributedString.alloc().initWithString_attributes_(
            "H" if choice == "five_hour" else "W", {
                A.NSFontAttributeName: A.NSFont.systemFontOfSize_weight_(8.5, A.NSFontWeightBold),
                A.NSForegroundColorAttributeName: A.NSColor.blackColor(),
            })
        marker.drawAtPoint_((14 - marker.size().width / 2, 0))
        separator = NSAttributedString.alloc().initWithString_attributes_("·", {
            A.NSFontAttributeName: A.NSFont.systemFontOfSize_(13),
            A.NSForegroundColorAttributeName: A.NSColor.blackColor(),
        })
        separator.drawAtPoint_((32 - separator.size().width / 2, 4))
    finally:
        image.unlockFocus()
    image.setTemplate_(True)
    return image


class QuotaPanel(NSObject):
    @objc.python_method
    def configure(self, controller, preferences=None):
        self.controller = controller
        self.preferences = preferences if preferences is not None else NSUserDefaults.alloc().initWithSuiteName_("io.github.codex-quota-bar")
        self.status = A.NSStatusBar.systemStatusBar().statusItemWithLength_(A.NSVariableStatusItemLength)
        self.button = self.status.button()
        self.button.setTarget_(self)
        self.button.setAction_("toggle:")
        self.button.setTitle_("演示" if controller.demo else "")
        self.button.setImagePosition_(A.NSImageLeft)
        self.button.setFont_(A.NSFont.monospacedDigitSystemFontOfSize_weight_(12, A.NSFontWeightBold))
        self.popover = A.NSPopover.alloc().init()
        self.popover.setBehavior_(A.NSPopoverBehaviorTransient)
        self.popover.setAnimates_(True)
        self.layout_key = None
        self.icon_key = None
        self.tick_(None)
        self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1, self, "tick:", None, True)
        NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    @objc.python_method
    def rect(self, x, top, width, height):
        return ((x, self.height - top - height), (width, height))

    @objc.python_method
    def text(self, title, x, top, width, size=13, bold=False, secondary=False, height=20):
        field = A.NSTextField.labelWithString_(title)
        field.setFrame_(self.rect(x, top, width, height))
        field.setFont_(A.NSFont.systemFontOfSize_weight_(size, A.NSFontWeightSemibold if bold else A.NSFontWeightRegular))
        field.setTextColor_(A.NSColor.secondaryLabelColor() if secondary else A.NSColor.labelColor())
        field.setLineBreakMode_(A.NSLineBreakByWordWrapping)
        field.setMaximumNumberOfLines_(2 if height > 24 else 1)
        self.content.addSubview_(field)
        return field

    @objc.python_method
    def glyph(self, name, title, x, top, color=None):
        view = A.NSImageView.alloc().initWithFrame_(self.rect(x, top, 22, 22))
        view.setImage_(symbol(name, title))
        view.setContentTintColor_(color or A.NSColor.secondaryLabelColor())
        self.content.addSubview_(view)

    @objc.python_method
    def separator(self, top):
        line = A.NSBox.alloc().initWithFrame_(self.rect(18, top, 304, 1))
        line.setBoxType_(A.NSBoxSeparator)
        self.content.addSubview_(line)

    @objc.python_method
    def action(self, title, name, selector, x, top, width):
        button = A.NSButton.buttonWithTitle_target_action_(title, self, selector)
        button.setFrame_(self.rect(x, top, width, 28))
        button.setBezelStyle_(A.NSBezelStyleRounded)
        button.setFont_(A.NSFont.systemFontOfSize_(12))
        button.setImage_(symbol(name, title))
        button.setImagePosition_(A.NSImageLeft)
        self.content.addSubview_(button)
        return button

    @objc.python_method
    def build(self, show_five):
        self.height = 490 if show_five else 402
        self.content = A.NSVisualEffectView.alloc().initWithFrame_(((0, 0), (340, self.height)))
        self.content.setMaterial_(A.NSVisualEffectMaterialPopover)
        self.content.setBlendingMode_(A.NSVisualEffectBlendingModeBehindWindow)
        self.content.setState_(A.NSVisualEffectStateActive)
        header_center = 24
        self.glyph("gauge.with.dots.needle.50percent", "Codex 额度", 18, header_center - 11)
        header = self.text("Codex 额度 · 演示" if self.controller.demo else "Codex 额度",
                           52, 0, 260, 16, True)
        header.setFont_(A.NSFont.systemFontOfSize_weight_(16, A.NSFontWeightBold))
        header_height = header.intrinsicContentSize().height
        header.setFrame_(self.rect(52, header_center - header_height / 2, 260, header_height))
        self.separator(48)
        self.rows = {}
        top = 62
        for key, title, name in (("five_hour", "五小时额度", "clock"), ("weekly", "每周额度", "calendar")):
            if key == "five_hour" and not show_five:
                continue
            self.glyph(name, title, 20, top + 2)
            self.text(title + "剩余", 54, top, 170, 14, True)
            value = self.text("—", 230, top, 90, 16, True)
            value.setAlignment_(A.NSTextAlignmentRight)
            bar = A.NSProgressIndicator.alloc().initWithFrame_(self.rect(54, top + 29, 266, 6))
            bar.setStyle_(A.NSProgressIndicatorStyleBar)
            bar.setIndeterminate_(False)
            bar.setMinValue_(0)
            bar.setMaxValue_(100)
            bar.setAccessibilityLabel_(title + "剩余")
            self.content.addSubview_(bar)
            detail = self.text("等待数据…", 54, top + 45, 266, 11, secondary=True)
            self.rows[key] = (value, bar, detail)
            top += 88
        self.separator(top - 6)
        row_center = top + 17  # Midpoint between the two separators.
        self.glyph("hourglass", "距离重置", 20, row_center - 11)
        self.reset_title = self.text("距离重置", 54, top, 140, 13, True)
        self.reset_value = self.text("--:--", 198, top, 122, 16, True)
        self.reset_value.setAlignment_(A.NSTextAlignmentRight)
        for field, x, width in ((self.reset_title, 54, 140), (self.reset_value, 198, 122)):
            height = field.intrinsicContentSize().height
            field.setFrame_(self.rect(x, row_center - height / 2, width, height))
        self.separator(top + 40)
        self.selectors = {}
        for offset, key, selector in ((52, "quotaWindow", "quotaChoice:"),
                                      (88, "countdownWindow", "timeChoice:")):
            self.text(CONTROL_LABELS[key], 20, top + offset + 4, 145, 12)
            self.selectors[key] = {}
            for x, choice in ((174, "weekly"), (250, "five_hour")):
                control = A.NSButton.buttonWithTitle_target_action_(WINDOW_LABELS[choice], self, selector)
                control.setFrame_(self.rect(x, top + offset, 72, 28))
                control.setBezelStyle_(A.NSBezelStyleRounded)
                control.setButtonType_(A.NSPushOnPushOffButton)
                control.setFont_(A.NSFont.systemFontOfSize_(12))
                control.setTag_(WINDOWS.index(choice))
                control.setAccessibilityLabel_(CONTROL_LABELS[key] + "：" + WINDOW_LABELS[choice])
                self.content.addSubview_(control)
                self.selectors[key][choice] = control
        top += 36
        self.message = self.text("正在读取…", 20, top + 94, 300, 11, secondary=True, height=34)
        self.refresh_button = self.action("刷新", "arrow.clockwise", "refresh:", 18, top + 134, 88)
        self.action("用量页面", "arrow.up.right.square", "usage:", 112, top + 134, 116)
        self.action("退出", "power", "quit:", 234, top + 134, 88)
        self.auto = A.NSButton.checkboxWithTitle_target_action_("登录系统时启动", self, "startup:")
        self.auto.setFrame_(self.rect(20, top + 174, 180, 22))
        self.auto.setFont_(A.NSFont.systemFontOfSize_(11))
        self.auto.setState_(A.NSControlStateValueOn if startup.is_enabled() else A.NSControlStateValueOff)
        self.content.addSubview_(self.auto)
        self.text("v" + __version__, 268, top + 176, 54, 11, secondary=True)
        if not hasattr(self, "view_controller"):
            self.view_controller = A.NSViewController.alloc().init()
            self.popover.setContentViewController_(self.view_controller)
        self.view_controller.setView_(self.content)
        self.popover.setContentSize_((340, self.height))

    def tick_(self, _):
        title, details = self.controller.tick()
        now = time.time()
        quota = self.controller.quota
        show_five = bool(quota and quota.five_hour is not None)
        if show_five != self.layout_key:
            self.build(show_five)
            self.layout_key = show_five
        quota_choice = selected_window(self.preferences, "quotaWindow", quota)
        time_choice = selected_window(self.preferences, "countdownWindow", quota)
        quota_window = getattr(quota, quota_choice) if quota else None
        time_window = getattr(quota, time_choice) if quota else None
        for preference, selection in (("quotaWindow", quota_choice), ("countdownWindow", time_choice)):
            for choice, control in self.selectors[preference].items():
                control.setState_(A.NSControlStateValueOn if choice == selection else A.NSControlStateValueOff)
        key = (quota_choice, quota_window, fraction(quota_window, now))
        if key != self.icon_key:
            self.button.setImage_(status_image(quota_window, now, quota_choice))
            self.icon_key = key
        time_text = countdown(time_window, now, show_days=time_choice == "weekly")
        warning = bool(self.controller.error) or bool(quota and now - quota.fetched_at > 180)
        self.button.setTitle_(("! " if warning else "") + time_text + (" [演示]" if self.controller.demo else ""))
        summary = ("图标：" + WINDOW_LABELS[quota_choice] + "剩余 " + remaining_text(quota_window, now)
                   + "；倒计时：" + WINDOW_LABELS[time_choice] + " " + time_text)
        self.button.setToolTip_("Codex 额度\n" + summary + "\n" + title)
        self.button.setAccessibilityLabel_("Codex 额度，" + summary + "，" + title)
        for name, (value, bar, detail) in self.rows.items():
            window = getattr(quota, name) if quota else None
            value.setStringValue_(remaining_text(window, now))
            amount = fraction(window, now)
            bar.setHidden_(amount is None)
            bar.setDoubleValue_(amount * 100 if amount is not None else 0)
            detail.setStringValue_(("重置于 " + reset_text(window)) if window else "未提供此额度窗口")
        self.reset_title.setStringValue_(WINDOW_LABELS[time_choice] + "重置倒计时")
        self.reset_value.setStringValue_(time_text)
        self.message.setStringValue_("演示数据 · 不连接账户" if self.controller.demo else
                                     "正在刷新额度…" if self.controller.busy else details[-1])
        self.message.setToolTip_(self.message.stringValue())
        self.refresh_button.setEnabled_(not self.controller.busy and not self.controller.demo)

    def quotaChoice_(self, sender):
        self.preferences.setObject_forKey_(WINDOWS[sender.tag()], "quotaWindow")
        self.tick_(None)

    def timeChoice_(self, sender):
        self.preferences.setObject_forKey_(WINDOWS[sender.tag()], "countdownWindow")
        self.tick_(None)

    def toggle_(self, _):
        if self.popover.isShown():
            self.popover.performClose_(None)
        else:
            self.tick_(None)
            A.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            self.popover.showRelativeToRect_ofView_preferredEdge_(self.button.bounds(), self.button, A.NSMinYEdge)

    def refresh_(self, _):
        self.controller.refresh()
        self.tick_(None)

    def usage_(self, _):
        webbrowser.open("https://chatgpt.com/codex/settings/usage")

    def startup_(self, _):
        try:
            startup.set_enabled(bool(self.auto.state()))
        except (OSError, UsageError):
            alert = A.NSAlert.alloc().init()
            alert.setMessageText_("无法修改开机启动设置")
            alert.setInformativeText_("请检查用户目录权限和 Codex 路径。")
            alert.runModal()
        self.auto.setState_(A.NSControlStateValueOn if startup.is_enabled() else A.NSControlStateValueOff)

    def quit_(self, _):
        self.timer.invalidate()
        A.NSApplication.sharedApplication().terminate_(None)


def run(controller, smoke_test=False):
    app = A.NSApplication.sharedApplication()
    app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)
    panel = QuotaPanel.alloc().init()
    panel.configure(controller)
    if smoke_test:
        panel.toggle_(None)
        panel.quit_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            3, panel, "quit:", None, False)
    app.run()
