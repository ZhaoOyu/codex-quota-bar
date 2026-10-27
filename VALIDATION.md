# Validation record

Local environment: Ubuntu Linux, Python 3.14. Updated: 2026-10-27.

- 37 automated unit and process integration tests pass: `python3 -m unittest discover -s tests -v`. Presentation tests cover weekly-only countdowns spanning multiple days, missing/expired resets, five-hour countdown priority, exhausted quotas, loading/error states and changing window availability.
- Protocol integration uses a real child process with deterministic synthetic responses; no account credentials or network are needed.
- Ubuntu DEB built with `scripts/build_deb.py`; metadata, package paths and permissions inspected; extracted launcher checked with `--demo --once`.
- Demo CLI verified in text and JSON modes.
- Real `--once` succeeded on 2026-10-22 using the local signed-in Codex CLI in the normal host environment. Both five-hour and weekly quota values and reset timestamps were returned. The restricted sandbox still prevents Codex from writing to its runtime directory; this is distinct from a failure on the user's Mac.
- Ubuntu native module imports checked with the Ayatana typelib. GUI startup cannot be validated in this execution environment: access to the display and creation of Xvfb listening sockets are restricted.
- macOS is not available locally. The v0.1.0 GitHub Actions run passed native GUI smoke tests and builds on Intel and Apple Silicon, but a user subsequently reported missing live quota data on macOS. Demo smoke tests did not establish real account connectivity.
- v0.1.1 adds minimal-PATH bundled subprocess testing in CI, Node discovery fixes and startup error classification. Real account connectivity on the affected Mac remains unverified until that user tests the new version.
- The public repository is https://github.com/ZhaoOyu/codex-quota-bar. v0.1.0 was released successfully; consult Releases and Actions for the current v0.1.1 publication status.

Before distributing a release, require the included GitHub Actions workflow to pass, then confirm live `--once` and panel text on a signed-in Ubuntu desktop and Mac. Tests of the synthetic protocol do not replace those checks.
