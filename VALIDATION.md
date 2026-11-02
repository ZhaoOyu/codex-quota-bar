# Validation record

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
