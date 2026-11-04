# Codex Quota Bar

See how much Codex quota you have left and when it resets, right in the Mac menu bar or Ubuntu top panel.

**[Download for Apple Silicon](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.8/codex-quota-bar-macos-arm64.zip)** · [Intel Mac](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.8/codex-quota-bar-macos-x86_64.zip) · [Ubuntu](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.8/codex-quota-bar_0.1.8_all.deb) · [简体中文](README.md)

<img src="docs/images/menubar-016.png" width="320" alt="A five-hour quota ring at 78% and a weekly quota track at 62%, both with a reset countdown">

**H** means five hours and **W** means weekly. Choose the quota window and the countdown separately. For example, you can watch your weekly balance while counting down to your next five-hour reset.

<img src="docs/images/quota-panel-en-017.png" width="360" alt="Quota panel with balances, reset times and menu bar display choices">

- Choose **Ring** to keep your balance visible, with an optional countdown. Choose **Track** to show the number, the countdown or both. Click the previews to select what appears.
- Open the panel for reset dates, automatic updates every minute and a shortcut to your usage page.

## Get started

Sign in to Codex CLI with your ChatGPT account. If this is your first sign-in, run `codex login` in Terminal.

On **macOS 13 or later**, unzip the download, drag Codex Quota Bar into Applications and open it. On **Ubuntu 22.04 or later**, install the downloaded package with `sudo apt install ./codex-quota-bar_0.1.8_all.deb`. GNOME users need Ubuntu AppIndicators enabled.

On Ubuntu, clicking the indicator opens readings and controls directly: refresh, quota/countdown window selection, appearance, visible content, startup and language. The detailed panel remains optional. Track mode uses a fixed-size icon with quota/countdown text beside it, avoiding squeezed wide tray images. The macOS track and panel are unchanged.

[Release notes](https://github.com/ZhaoOyu/codex-quota-bar/releases/tag/v0.1.8) · [Report an issue](https://github.com/ZhaoOyu/codex-quota-bar/issues)

The interface follows your system language by default. Open **Language** at the bottom of the panel to switch to **简体中文** or **English**.

## More menu bar apps

- [Mingdu](https://github.com/ZhaoOyu/mingdu/blob/main/README.en.md) · Adjust the brightness of your built-in and external displays separately, or apply a night, everyday, or bright preset to all of them at once.
- [Fengdu](https://github.com/ZhaoOyu/fengdu/blob/main/README.en.md) · Monitor chip temperature and fan speeds on an Apple Silicon Mac with a fan. Set a target RPM or choose a fan curve that responds to temperature.
