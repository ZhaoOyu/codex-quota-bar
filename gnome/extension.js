import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const BUS = 'io.github.ZhaoOyu.CodexQuotaBar';
const PATH = '/io/github/ZhaoOyu/CodexQuotaBar';
const IFACE = 'io.github.ZhaoOyu.CodexQuotaBar1';

function label(text = '', style = '', expand = false) {
    return new St.Label({text, style_class: style, x_expand: expand,
        y_align: Clutter.ActorAlign.CENTER});
}

function button(text, callback) {
    const widget = new St.Button({label: text, style_class: 'button codex-choice',
        reactive: true, can_focus: true});
    widget.connect('clicked', callback);
    return widget;
}

function selected(widget, active) {
    if (active)
        widget.add_style_pseudo_class('checked');
    else
        widget.remove_style_pseudo_class('checked');
}

function drawProgress(area, track, value) {
    const cr = area.get_context();
    try {
        const [width, height] = area.get_surface_size();
        if (width < 4 || height < 4)
            return;
        const color = area.get_theme_node().get_foreground_color();
        const source = alpha => cr.setSourceRGBA(color.red / 255, color.green / 255,
            color.blue / 255, alpha * color.alpha / 255);
        const part = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
        if (!track) {
            source(0.18);
            cr.rectangle(0, 0, width, height);
            cr.fill();
            source(0.95);
            cr.rectangle(0, 0, width * part, height);
            cr.fill();
            return;
        }
        const radius = (height - 4) / 2;
        const left = 2 + radius;
        const right = Math.max(left, width - 2 - radius);
        const cy = height / 2;
        cr.moveTo(left, 2);
        cr.lineTo(right, 2);
        cr.arc(right, cy, radius, -Math.PI / 2, Math.PI / 2);
        cr.lineTo(left, height - 2);
        cr.arc(left, cy, radius, Math.PI / 2, 3 * Math.PI / 2);
        cr.closePath();
        cr.setLineWidth(2);
        source(0.28);
        cr.strokePreserve();
        if (part > 0) {
            const perimeter = 2 * (right - left) + 2 * Math.PI * radius;
            cr.setDash([perimeter * part, perimeter + 1], 0);
            source(1);
            cr.stroke();
        }
    } finally {
        cr.$dispose();
    }
}

export default class CodexQuotaPanel extends Extension {
    enable() {
        this._generation = (this._generation ?? 0) + 1;
        const generation = this._generation;
        this._alive = true;
        this._healthy = false;
        this._pending = false;
        this._cancellable = new Gio.Cancellable();
        this._indicator = new PanelMenu.Button(0.0, 'Codex Quota');
        const tray = new St.BoxLayout({style_class: 'codex-tray'});
        this._icon = new St.Icon({icon_name: 'utilities-system-monitor-symbolic', icon_size: 24});
        this._track = new St.Widget({layout_manager: new Clutter.BinLayout(),
            y_align: Clutter.ActorAlign.CENTER});
        this._trackArea = new St.DrawingArea({x_expand: true, y_expand: true});
        this._trackLabel = label('', 'codex-track-label');
        this._trackArea.connect('repaint', area => drawProgress(area, true, this._fraction));
        this._track.add_child(this._trackArea);
        this._track.add_child(this._trackLabel);
        this._label = label('Codex …');
        tray.add_child(this._icon);
        tray.add_child(this._track);
        tray.add_child(this._label);
        this._indicator.add_child(tray);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        this._offline();
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START,
            null, BUS, PATH, IFACE, this._cancellable, (_source, result) => {
                if (!this._alive || generation !== this._generation)
                    return;
                try {
                    this._proxy = Gio.DBusProxy.new_for_bus_finish(result);
                    this._ownerSignal = this._proxy.connect('notify::g-name-owner', () => {
                        this._healthy = false;
                        this._offline();
                        this._refresh();
                    });
                    this._stateSignal = this._proxy.connect('g-signal', (_proxy, _sender, name, params) => {
                        if (name === 'StateChanged' && this._proxy.g_name_owner)
                            this._receive(params.deep_unpack()[0]);
                    });
                    this._refresh();
                } catch (error) {
                    if (!this._cancellable.is_cancelled())
                        console.error(`Codex panel connection failed: ${error.message}`);
                }
            });
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _call(method, signature = null, values = [], cancellable = this._cancellable) {
        return new Promise((resolve, reject) => {
            if (!this._proxy?.g_name_owner) {
                reject(new Error('Codex Quota Bar is not running'));
                return;
            }
            this._proxy.call(method, signature ? new GLib.Variant(signature, values) : null,
                Gio.DBusCallFlags.NO_AUTO_START, 3000, cancellable, (proxy, result) => {
                    try {
                        resolve(proxy.call_finish(result).deep_unpack());
                    } catch (error) {
                        reject(error);
                    }
                });
        });
    }

    async _refresh() {
        if (!this._alive || this._pending || !this._proxy?.g_name_owner)
            return;
        this._pending = true;
        const owner = this._proxy.g_name_owner;
        const generation = this._generation;
        try {
            const [json] = await this._call('GetState');
            if (!this._alive || generation !== this._generation || owner !== this._proxy.g_name_owner)
                return;
            this._receive(json);
            if (this._healthy)
                await this._call('Claim'); // Renewable lease; tray recovers if we stop.
        } catch (_error) {
            if (this._alive && generation === this._generation)
                this._offline();
        } finally {
            if (generation === this._generation)
                this._pending = false;
        }
    }

    _receive(json) {
        if (!this._alive)
            return;
        try {
            const state = JSON.parse(json);
            if (state.protocol !== 1)
                throw new Error('Unsupported quota protocol');
            this._apply(state);
            this._healthy = true;
        } catch (error) {
            this._healthy = false;
            this._call('Release').catch(() => {});
            this._offline();
            console.error(`Codex panel update failed: ${error.message}`);
        }
    }

    _offline() {
        if (!this._alive)
            return;
        this._healthy = false;
        this._signature = null;
        this._ui = null;
        this._track.hide();
        this._icon.hide();
        this._label.text = 'Codex !';
        this._label.show();
        this._indicator.menu.removeAll();
        const message = new PopupMenu.PopupMenuItem('请启动或更新 Codex Quota Bar / Start or update the app',
            {reactive: false});
        this._indicator.menu.addMenuItem(message);
        this._indicator.menu.addAction('启动 / Start Codex Quota Bar', () => {
            try {
                const app = Gio.DesktopAppInfo.new('codex-quota-bar.desktop');
                if (!app)
                    throw new Error('Install Codex Quota Bar 0.1.11 or later');
                app.launch([], null);
            } catch (error) {
                Main.notify('Codex Quota Bar', error.message);
            }
        });
    }

    _action(method, signature = null, values = []) {
        this._call(method, signature, values).then(() => this._refresh()).catch(() => {
            if (this._alive && this._ui)
                this._ui.status.text = '操作失败，请重试 / Action failed; retry';
        });
    }

    _build(state) {
        this._indicator.menu.removeAll();
        const item = new PopupMenu.PopupBaseMenuItem({reactive: true, can_focus: false,
            activate: false, hover: false});
        const root = new St.BoxLayout({vertical: true, style_class: 'codex-panel'});
        item.add_child(root);
        this._indicator.menu.addMenuItem(item);
        root.add_child(label(state.title, 'codex-heading'));
        const ui = this._ui = {sections: {}, choices: {}};
        for (const section of state.sections) {
            const box = new St.BoxLayout({vertical: true, style_class: 'codex-section'});
            const row = new St.BoxLayout({style_class: 'codex-row'});
            row.add_child(label(section.title, '', true));
            const value = label('', 'codex-value');
            row.add_child(value);
            box.add_child(row);
            const bar = new St.DrawingArea({height: 6, x_expand: true});
            bar.connect('repaint', area => drawProgress(area, false, ui.sections[section.key]?.fraction));
            box.add_child(bar);
            const detail = label('', 'codex-detail');
            box.add_child(detail);
            root.add_child(box);
            ui.sections[section.key] = {box, value, bar, detail};
        }
        const reset = new St.BoxLayout({style_class: 'codex-row'});
        ui.resetTitle = label('', '', true);
        ui.reset = label('', 'codex-value');
        reset.add_child(ui.resetTitle);
        reset.add_child(ui.reset);
        root.add_child(reset);
        for (const group of state.controls) {
            const row = new St.BoxLayout({style_class: 'codex-controls'});
            row.add_child(label(group.title, '', true));
            for (const choice of group.choices) {
                const widget = button(choice.label, () => {
                    if (group.key === 'parts')
                        this._action('TogglePart', '(u)', [Number(choice.value)]);
                    else
                        this._action('SetPreference', '(ss)', [group.key, choice.value]);
                });
                row.add_child(widget);
                ui.choices[`${group.key}/${choice.value}`] = widget;
            }
            root.add_child(row);
        }
        ui.status = label('', 'codex-detail');
        ui.status.clutter_text.line_wrap = true;
        ui.status.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        root.add_child(ui.status);
        const actions = new St.BoxLayout({style_class: 'codex-controls'});
        ui.refresh = button(state.actions.refresh, () => this._action('Refresh'));
        actions.add_child(ui.refresh);
        actions.add_child(button(state.actions.usage, () => this._action('Usage')));
        actions.add_child(button(state.actions.quit, () => this._action('Quit')));
        root.add_child(actions);
        ui.startup = button(state.startupLabel, () => this._action('SetStartup', '(b)', [!this._startup]));
        root.add_child(ui.startup);
        root.add_child(label(`v${state.version}`, 'codex-detail'));
    }

    _apply(state) {
        const signature = JSON.stringify([state.title, state.version, state.startupLabel, state.actions,
            state.controls.map(group => [group.key, group.title, group.choices.map(c => [c.value, c.label])]),
            state.sections.map(section => [section.key, section.title])]);
        if (signature !== this._signature) {
            this._build(state);
            this._signature = signature;
        }
        const track = state.style === 'track';
        this._track.visible = track;
        this._icon.visible = !track;
        this._trackLabel.text = state.reading;
        this._fraction = state.fraction;
        this._trackArea.queue_repaint();
        if (!track && state.icon !== this._iconPath) {
            this._iconPath = state.icon;
            this._icon.gicon = Gio.FileIcon.new(Gio.File.new_for_path(state.icon));
        }
        this._label.text = state.label;
        this._label.visible = Boolean(state.label);
        for (const section of state.sections) {
            const widgets = this._ui.sections[section.key];
            widgets.box.visible = section.visible;
            widgets.value.text = section.value;
            widgets.detail.text = section.detail;
            widgets.fraction = section.fraction;
            widgets.bar.visible = section.fraction !== null;
            widgets.bar.queue_repaint();
        }
        this._ui.resetTitle.text = state.countdownTitle;
        this._ui.reset.text = state.countdown;
        this._ui.status.text = state.status;
        for (const group of state.controls) {
            for (const choice of group.choices) {
                const widget = this._ui.choices[`${group.key}/${choice.value}`];
                selected(widget, choice.selected);
                widget.reactive = choice.enabled;
                widget.can_focus = choice.enabled;
                widget.opacity = choice.enabled ? 255 : 140;
            }
        }
        this._ui.refresh.reactive = state.refreshEnabled;
        this._ui.refresh.can_focus = state.refreshEnabled;
        this._ui.refresh.opacity = state.refreshEnabled ? 255 : 140;
        this._startup = state.startup;
        selected(this._ui.startup, state.startup);
    }

    disable() {
        this._alive = false;
        this._healthy = false;
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = null;
        if (this._proxy) {
            this._call('Release', null, [], null).catch(() => {});
            this._proxy.disconnect(this._ownerSignal);
            this._proxy.disconnect(this._stateSignal);
        }
        this._cancellable.cancel();
        this._proxy = null;
        this._indicator.destroy();
        this._indicator = null;
        this._ui = null;
        this._signature = null;
        this._iconPath = null;
    }
}
