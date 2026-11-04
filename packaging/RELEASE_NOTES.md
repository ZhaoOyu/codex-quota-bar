# Codex 余量 0.1.8

修复 Ubuntu 跑道显示与点击交互：

- 跑道改为固定尺寸图标，额度数值和倒计时使用独立的顶栏文字，避免长条图标被缩小或截断。
- 点击顶栏直接展开可操作菜单：查看额度/重置时间、刷新、选择额度窗口与样式、显示内容、开机启动和语言。
- 保留独立详细面板入口，兼容原有显示偏好；Mac 跑道与面板不变。

Ubuntu now uses a fixed-size track icon plus a native text label, avoiding squashed wide tray images. Clicking the indicator opens quota readings and controls directly. Refresh, display settings, startup and language no longer require opening a second panel. The detailed panel remains optional; macOS behavior is unchanged.

退出旧版后，安装新版 Ubuntu DEB 即可覆盖升级，无需先卸载。

[中文使用指南](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.8/README.md) · [English guide](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.8/README.en.md)
