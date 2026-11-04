// Test-only extension, copied into an isolated headless Shell. Never packaged.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const UUID = 'codex-quota-bar@zhaooyu.github.io';
const sleep = ms => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
    resolve();
    return GLib.SOURCE_REMOVE;
}));
function assert(value, message) {
    if (!value)
        throw new Error(message);
}

export default class TestDriver extends Extension {
    enable() {
        // GNOME temporarily re-enables extensions later in load order when an
        // earlier extension is disabled. Keep this one test run alive.
        if (global.__codexQuotaTestStarted)
            return;
        global.__codexQuotaTestStarted = true;
        this._run().catch(error => this._result({ok: false, error: String(error), stack: error.stack}));
    }

    _result(value) {
        const path = GLib.getenv('CODEX_GNOME_TEST_RESULT');
        GLib.file_set_contents(path, JSON.stringify(value));
    }

    async _run() {
        let app;
        for (let n = 0; n < 160; n++) {
            app = Main.extensionManager.lookup(UUID)?.stateObj;
            if (app?._healthy)
                break;
            await sleep(250);
        }
        assert(app?._healthy, 'Quota extension did not connect');
        Main.overview.hide();
        await sleep(500);
        app._indicator.menu.open();
        await sleep(700);
        assert(app._indicator.menu.isOpen, 'Native popup did not open');
        assert(app._ui.sections.weekly.value.text === '62%', 'Weekly reading missing');
        assert(app._ui.sections.five_hour.value.text === '78%', 'Five-hour reading missing');
        app._ui.choices['indicatorStyle/track'].emit('clicked', 1);
        await sleep(500);
        app._ui.choices['quotaWindow/weekly'].emit('clicked', 1);
        await sleep(500);
        assert(app._track.visible && app._trackLabel.text.includes('W 62'), 'Track selection failed');
        assert(app._track.width > 40 && app._track.height > 8, 'Track allocation invalid');
        app._ui.choices['countdownWindow/weekly'].emit('clicked', 1);
        await sleep(500);
        assert(app._ui.reset.text.includes('天'), 'Weekly countdown selection failed');
        app._ui.choices['interfaceLanguage/en'].emit('clicked', 1);
        await sleep(500);
        assert(app._ui.refresh.label === 'Refresh', 'Language switch failed');
        app._ui.choices['interfaceLanguage/zh-Hans'].emit('clicked', 1);
        await sleep(500);
        app._indicator.menu.open();
        await sleep(500);
        const controls = Object.values(app._ui.choices).map(widget => ({
            label: widget.label, visible: widget.visible, opacity: widget.get_paint_opacity(),
            position: widget.get_transformed_position(), size: widget.get_transformed_size(),
        }));
        assert(controls.every(c => c.visible && c.opacity > 0 && c.size[0] > 0 && c.size[1] > 0),
            'A panel control is not visibly allocated');
        const stream = Gio.File.new_for_path(GLib.getenv('CODEX_GNOME_TEST_IMAGE')).replace(null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        await new Shell.Screenshot().screenshot(false, stream);
        stream.close(null);
        app._indicator.menu.toggle();
        assert(!app._indicator.menu.isOpen, 'Second activation did not close popup');
        app._indicator.menu.toggle();
        assert(app._indicator.menu.isOpen, 'Popup did not reopen');
        // Verify actual disable removes actors and releases the tray lease.
        await Main.extensionManager.disableExtension(UUID);
        await sleep(500);
        assert(!Main.panel.statusArea[UUID], 'Panel button leaked after disable');
        await Main.extensionManager.enableExtension(UUID);
        await sleep(1200);
        app = Main.extensionManager.lookup(UUID)?.stateObj;
        assert(app?._healthy, 'Re-enable did not reconnect');
        this._result({ok: true, controls, checks: ['native popup', 'quota readings', 'track allocation',
            'display controls', 'language', 'toggle close/reopen', 'disable/re-enable']});
    }

    disable() {}
}
