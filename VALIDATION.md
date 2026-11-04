# Validation record

## Ubuntu direct controls and track sizing — 2026-11-04

- Started from remote main commit `73487b9` after downloading the v0.1.7 Ubuntu DEB and verifying its SHA256 against the release checksums.
- The old track embedded all text in a variable-width SVG. Ubuntu's AppIndicator host controls icon sizing; the new track uses a 24 × 24 canvas and a separate native label for quota/countdown text.
- Primary-click controls are exported as standard menu items, including quota/reset readings, refresh, window/style selection, visible content, startup and language. The optional detailed panel remains available. No unsupported primary-activation signal is required.
- On the Ubuntu host, `/usr/bin/python3 -W ignore::DeprecationWarning -m unittest discover -s tests -q` ran 72 tests: 60 passed and 12 macOS-only tests were skipped. Native GTK tests used temporary preference files; startup and external URL actions were mocked. No user settings were changed.
- Tests cover square track rendering, separate labels, direct menu controls, language rebuilding, failed preference writes, errors and weekly-only data. This is widget-level interaction validation, not an end-to-end pointer test of GNOME Shell.
- The v0.1.8 DEB was built locally and extracted without installing over the user's version. Its packaged launcher passed `--demo --once` and the three-second GTK `--demo --smoke-test`.
- Existing macOS behavior is unchanged; cross-platform CI remains required for release builds.

## Ubuntu interface parity — 2026-11-02

Environment: Ubuntu 22.04 ARM64 in OrbStack, system Python 3.10, GTK 3.24.33, Ayatana AppIndicator 0.5.90, Cairo, Xvfb and Openbox. The host development machine is macOS.

- The Ubuntu interface now shares selection and quota-validity rules with macOS. It uses a symbolic quota ring, bold native-font outlines, H/W markers, a dot-separated countdown and a GTK details panel with two independent weekly/five-hour button rows.
- All 63 discovered checks passed across the two platforms: Ubuntu ran 52 and skipped 11 AppKit checks; macOS ran 54 and skipped 9 native GTK checks.
- Linux checks run under D-Bus and Xvfb, including real GTK button callbacks, persistence and failed writes, weekly-only and missing selected windows, zero versus expired data, errors, stale data and menu activation. Native symbolic loading checks that the ring remains hollow, keeps both glyph regions and preserves the progress track's lower opacity. Plain SVG loading alone did not catch GTK's symbolic recoloring behavior.
- Light and dark Adwaita renders were inspected under Openbox. Header and countdown rows align vertically; panel visibility was confirmed with a window manager. Screenshots use explicitly labelled demo data, not account data.
- The Ubuntu 22.04 tray API exposes a menu rather than arbitrary GTK controls. Open the native panel via “打开额度面板”, or middle-click where the desktop supports secondary activation. Newer Ayatana primary activation is connected when available. A full GNOME Shell / Wayland session and its exact tray sizing/spacing have not been visually validated here.
- The DEB was built, installed in the Ubuntu VM without optional GNOME packages, and its installed launcher passed `--demo --once` and the GTK smoke test. Both bundled symbolic icons were included. CI installs Cairo and the SVG loader and runs native GTK tests under Xvfb.
- GitHub also exposed an existing macOS bundle-only crash: `NSUserDefaults` rejects a named suite equal to the running bundle identifier. The app now uses standard defaults inside its bundle and the same named domain when run from source, preserving stored choices. A locally built ARM64 app passed its packaged GUI smoke test after the fix.
- Ordinary startup continues to use the existing real Codex JSON-RPC controller. No Linux account credentials were copied to the VM; live account access in that VM is not claimed.


## Native macOS interface — 2026-11-02

Environment: macOS, Homebrew Python 3.13.4, project-local virtual environment, PyObjC 13.0.

- All 50 tests passed with `python -m unittest discover -s tests -q`: 39 quota/protocol/controller/startup checks and 11 native AppKit checks. Test data is synthetic; startup registration and opening external pages are mocked.
- The native popover smoke test passed: `python -m codex_quota_bar --demo --smoke-test` opens the panel and exits after three seconds.
- Native tests exercise direct weekly/five-hour button selection, mutually exclusive selected states, repeat selection, independent preferences, preference reloading, missing selected windows, weekly-only layout, stale/expired data and error clearing.
- Actual native component renders were inspected for layout. The quota icon uses a 35 × 24-point template image, a 10.7-point radius and 2.4-point stroke, bold values and an H/W marker in the bottom gap. Header and reset-row elements share vertical centers.
- Live `--once --json` and the background-polling native UI successfully read a signed-in account. The account returned a weekly window and no five-hour window. This verifies that missing five-hour data is handled without inventing a value; returned values are not hard-coded.
- README images are generated from explicitly labelled demo data. They are native component renders, not private account screenshots. View snapshots do not reproduce the window server's live background blur or shadow.
- A separate desktop automation connection timed out. Native control callbacks and rendering were verified, but end-to-end pointer automation is not recorded as passed.
- Ubuntu GUI execution and packaged application builds were not rerun locally for this change; the repository workflow checks these on the supported CI platforms. Inspect the Actions run for the exact commit before distributing packages.

## Earlier validation — 2026-10-27

Environment: Ubuntu Linux, Python 3.14. These records refer to earlier versions and do not establish validation of the current macOS implementation.

- All 39 unit and process integration tests passed, including weekly-only countdowns and boundary cases.
- Protocol integration used a real child process with deterministic synthetic responses, without credentials or network access.
- An Ubuntu DEB was built with `scripts/build_deb.py`; metadata, paths and permissions were inspected, and the extracted launcher passed `--demo --once`.
- Demo CLI text and JSON modes were checked.
- Live `--once` succeeded on 2026-10-22 outside the restricted sandbox, returning both five-hour and weekly windows.
- Ubuntu native module imports succeeded with the Ayatana typelib. GUI startup could not be checked in that local environment because display access and Xvfb sockets were restricted.
- The v0.1.0 GitHub Actions run passed GUI smoke tests and Intel/Apple Silicon builds. A later macOS live-connectivity report showed why demo tests alone are insufficient.
- v0.1.1 added minimal-PATH bundled subprocess checks, Node discovery fixes and startup error classification.

Before distributing a release, require the included GitHub Actions workflow to pass and confirm live `--once` plus panel display on a signed-in Ubuntu desktop and Mac.
