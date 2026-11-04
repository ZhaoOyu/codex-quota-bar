"""Session-only GNOME bridge. Exports display state, never credentials or paths to Codex."""
import json
from pathlib import Path
import time

from gi.repository import Gio, GLib

from . import __version__, language
from .display import APPEARANCE, CONTROL_LABELS, WINDOW_LABELS, appearance, choose_window, fraction, track_reading
from .language import tr
from .model import countdown

BUS_NAME = "io.github.ZhaoOyu.CodexQuotaBar"
OBJECT_PATH = "/io/github/ZhaoOyu/CodexQuotaBar"
INTERFACE = "io.github.ZhaoOyu.CodexQuotaBar1"
XML = Path(__file__).with_name("shell-interface.xml").read_text()


def snapshot(panel):
    quota, now = panel.controller.quota, time.time()
    quota_choice = choose_window(panel.preferences.get("quotaWindow"), quota)
    time_choice = choose_window(panel.preferences.get("countdownWindow"), quota)
    window = getattr(quota, quota_choice) if quota else None
    time_window = getattr(quota, time_choice) if quota else None
    style = appearance("indicatorStyle", panel.preferences.get("indicatorStyle"))
    parts = panel.visible_parts(style)
    time_text = tr(countdown(time_window, now, show_days=time_choice == "weekly"))
    reading = " · ".join(value for bit, value in (
        (1, track_reading(window, now, quota_choice, "")), (2, time_text)) if parts & bit)
    controls = []
    for key, title in CONTROL_LABELS.items():
        selected = quota_choice if key == "quotaWindow" else time_choice
        controls.append({"key": key, "title": tr(title), "choices": [
            {"value": value, "label": tr(label), "selected": value == selected, "enabled": True}
            for value, label in WINDOW_LABELS.items()]})
    controls.append({"key": "indicatorStyle", "title": tr(APPEARANCE["indicatorStyle"][0]), "choices": [
        {"value": value, "label": tr(label), "selected": value == style, "enabled": True}
        for value, label in APPEARANCE["indicatorStyle"][1].items()]})
    controls.append({"key": "parts", "title": tr("显示内容"), "choices": [
        {"value": str(bit), "label": tr(label), "selected": bool(parts & bit),
         "enabled": style == "track" or bit == 2}
        for bit, label in ((1, "额度数值"), (2, "倒计时"))]})
    controls.append({"key": "interfaceLanguage", "title": "Language" if language.english() else "语言",
                     "choices": [{"value": value, "label": label, "selected": language.choice == value, "enabled": True}
                                 for value, label in zip(language.CHOICES, language.names())]})
    return {"protocol": 1, "version": __version__, "title": panel.header.get_text(),
            "style": style, "reading": reading, "fraction": fraction(window, now),
            "icon": panel.indicator.get_icon(), "label": panel.indicator.get_label(),
            "sections": [{"key": key, "title": tr(WINDOW_LABELS[key] + "额度剩余"),
                          "value": widgets[0].get_text(), "detail": widgets[2].get_text(),
                          "fraction": fraction(getattr(quota, key) if quota else None, now),
                          "visible": panel.sections[key].get_visible()}
                         for key, widgets in panel.rows.items()],
            "countdownTitle": panel.reset_title.get_text(), "countdown": panel.reset_value.get_text(),
            "status": panel.message.get_text(), "controls": controls,
            "refreshEnabled": panel.refresh_button.get_sensitive(),
            "startup": panel.auto.get_active(), "startupLabel": tr("登录系统时启动"),
            "actions": {key: tr(label) for key, label in (("refresh", "刷新"), ("usage", "用量页面"), ("quit", "退出"))}}


class ShellBridge:
    def __init__(self, panel, bus_name=BUS_NAME):
        self.panel = panel
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.peer = None
        self.expires = 0
        self.last_state = ""
        self.closed = False
        self.registration = self.connection.register_object(
            OBJECT_PATH, Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0], self.call, None, None)
        self.owner = Gio.bus_own_name_on_connection(self.connection, bus_name,
            Gio.BusNameOwnerFlags.DO_NOT_QUEUE, None, self.name_lost)
        self.watch = self.connection.signal_subscribe("org.freedesktop.DBus", "org.freedesktop.DBus",
            "NameOwnerChanged", "/org/freedesktop/DBus", None, Gio.DBusSignalFlags.NONE, self.owner_changed)

    def name_lost(self, *_):
        self.release()

    def release(self):
        self.peer = None
        self.expires = 0
        self.panel.set_shell_attached(False)

    def owner_changed(self, connection, sender, path, interface, signal, parameters):
        name, old, new = parameters.unpack()
        if name == self.peer and not new:
            self.release()

    def call(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            values = parameters.unpack()
            if method == "GetState":
                invocation.return_value(GLib.Variant("(s)", (json.dumps(snapshot(self.panel), ensure_ascii=False),)))
                return
            if method == "Claim":
                if self.peer not in (None, sender) and time.monotonic() < self.expires:
                    raise ValueError("Another shell client is attached")
                self.peer, self.expires = sender, time.monotonic() + 15
                self.panel.set_shell_attached(True)
            elif method == "Release":
                if sender == self.peer:
                    self.release()
            elif method == "SetPreference":
                key, value = values
                if not self.panel.preferences.valid(key, value):
                    raise ValueError("Invalid display preference")
                if key == "interfaceLanguage":
                    self.panel.languages.set_active_id(value)
                else:
                    self.panel.select(None, key, value)
            elif method == "TogglePart":
                if values[0] not in (1, 2):
                    raise ValueError("Invalid display part")
                self.panel.toggle_part(None, values[0])
            elif method == "SetStartup":
                self.panel.auto.set_active(values[0])
            elif method == "Refresh":
                self.panel.refresh()
            elif method == "Usage":
                self.panel.usage()
            elif method == "Quit":
                from gi.repository import Gtk
                GLib.idle_add(lambda: (Gtk.main_quit(), False)[1])
            else:
                raise ValueError("Unknown action")
            self.panel.tick()
            invocation.return_value(GLib.Variant("()", ()))
        except Exception:
            # Do not expose filesystem paths, CLI arguments or exception details.
            invocation.return_dbus_error(INTERFACE + ".Error", "Action unavailable or invalid arguments")

    def publish(self):
        if self.closed:
            return
        if self.peer and time.monotonic() >= self.expires:
            self.release()
        state = json.dumps(snapshot(self.panel), ensure_ascii=False)
        if state != self.last_state:
            self.last_state = state
            self.connection.emit_signal(None, OBJECT_PATH, INTERFACE, "StateChanged", GLib.Variant("(s)", (state,)))

    def close(self):
        self.closed = True
        self.release()
        self.connection.signal_unsubscribe(self.watch)
        self.connection.unregister_object(self.registration)
        Gio.bus_unown_name(self.owner)
