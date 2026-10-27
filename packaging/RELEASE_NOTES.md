Codex Quota Bar displays your remaining five-hour quota, weekly quota and five-hour reset countdown in the macOS menu bar or Ubuntu top panel.

Version 0.1.2 hides five-hour quota and reset information when the account does not return that window. Weekly-only accounts show just their weekly quota in the status bar. Information rows now use enabled system text (black in light appearance, readable system text in dark appearance) instead of disabled grey text. Loading and errors show only their status message.

- Ubuntu: download the `.deb`, then `sudo apt install ./codex-quota-bar_0.1.2_all.deb`.
- macOS: choose `arm64` for Apple Silicon or `x86_64` for Intel; unzip and move the app to Applications.
- Prerequisite: install the Codex CLI and sign in with `codex login` using your ChatGPT account.
- macOS builds are not Developer ID signed or notarized. macOS may require approval in System Settings → Privacy & Security. Verify SHA256SUMS before opening.
- Ubuntu GNOME requires the AppIndicator extension enabled to show the panel indicator and its label.

每分钟刷新真实额度；每秒更新倒计时；菜单显示准确重置时间（本地时区），支持手动刷新及登录系统时启动。

This is an independent open-source utility, not an official OpenAI product. It uses the local Codex app-server rate-limit endpoint and does not run inference.

