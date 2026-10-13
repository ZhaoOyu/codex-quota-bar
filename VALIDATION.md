# Validation record

Local environment: Ubuntu Linux, Python 3.14. Date: 2026-10-13.

- Automated unit and process integration tests: `python3 -m unittest discover -s tests -v`.
- Protocol integration uses a real child process with deterministic synthetic responses; no account credentials or network are needed.
- Ubuntu DEB built with `scripts/build_deb.py`; metadata, package paths and permissions inspected; extracted launcher checked with `--demo --once`.
- Demo CLI verified in text and JSON modes.
- Real `--once` attempted: local Codex app-server cannot start because this execution environment restricts writes to Codex's runtime directory. Live quota retrieval has **not** been validated here.
- Ubuntu native module imports checked with the Ayatana typelib. GUI startup cannot be validated in this execution environment: access to the display and creation of Xvfb listening sockets are restricted.
- macOS is not available locally. Both Intel and Apple Silicon builds and native GUI smoke tests are configured in GitHub Actions; their success is **not** claimed until CI actually runs.
- GitHub publication requires an authenticated GitHub connection and a destination repository. No public repository or Release URL exists at the time of this local validation.

Before distributing a release, require the included GitHub Actions workflow to pass, then confirm live `--once` and panel text on a signed-in Ubuntu desktop and Mac. Tests of the synthetic protocol do not replace those checks.
