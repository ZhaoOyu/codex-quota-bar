# Codex 余量

五小时额度快用完时，离重置还有多久？把余量和倒计时放在 Mac 菜单栏或 Ubuntu 顶栏，写代码时抬眼就能看到。

**[下载 Mac 版（M 系列芯片）](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.9/codex-quota-bar-macos-arm64.zip)** · [Intel Mac](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.9/codex-quota-bar-macos-x86_64.zip) · [Ubuntu](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.9/codex-quota-bar_0.1.9_all.deb) · [English](README.en.md)

<img src="docs/images/menubar-016.png" width="320" alt="左侧圆环显示五小时额度剩余 78%，右侧跑道显示周额度剩余 62%">

左边的圆环看五小时余量，右边的跑道看周余量。两种样式都可以配上重置倒计时。

<img src="docs/images/quota-panel-016.png" width="360" alt="Codex 余量的 Mac 面板，同时展示周额度、五小时额度和重置倒计时，下方可切换圆环与跑道">

## 把最关心的数字放在手边

- **看两种额度。** 图标里的 H 代表五小时，W 代表每周。额度和倒计时可以分开选，比如左边看这周还剩多少，右边看五小时额度何时恢复。
- **自己决定占多少菜单栏空间。** 圆环把剩余比例围在数字外面。跑道可以只放额度、只放倒计时，或两者都放。点击面板里的预览即可切换，高亮的就是当前显示的内容。
- **点开看具体时间。** 面板列出账户可用的额度和重置时间，每分钟刷新。需要查看完整用量时，点击「用量页面」。

## 开始使用

先在本机用 ChatGPT 账号登录 Codex CLI。已经登录过就可以直接打开应用，首次登录可在终端运行 `codex login`。

**Mac（macOS 13 及以上）**　解压下载的 ZIP，把 Codex Quota Bar 拖入「应用程序」并打开。点击菜单栏图标，选择想看的额度。

**Ubuntu（22.04 及以上）**　在下载目录运行 `sudo apt install ./codex-quota-bar_0.1.9_all.deb`，然后从应用列表打开。使用 GNOME 时，请启用 Ubuntu AppIndicators 扩展。

Ubuntu 点击顶栏图标会直接展开可操作菜单，可查看额度和重置时间、刷新、切换额度窗口/样式/显示内容、设置开机启动及语言，无需先点击「打开额度面板」。该入口仍保留，用于打开独立详细面板。跑道围住额度数值和倒计时，宽度随文字自动调整，支持中文和高分屏。Ubuntu AppIndicators 的宽图像不会自动应用符号图标颜色，因此跑道使用适合默认深色顶栏的浅色绘制；自定义浅色顶栏可选用跟随主题的圆环。Mac 的跑道显示和面板不变。

[版本与校验文件](https://github.com/ZhaoOyu/codex-quota-bar/releases/tag/v0.1.9) · [使用问题](https://github.com/ZhaoOyu/codex-quota-bar/issues)

应用默认跟随系统语言。在面板底部打开「语言」，可随时选择「简体中文」或「English」。

## 更多菜单栏工具

- [明度](https://github.com/ZhaoOyu/mingdu) · 分别调节内置屏幕和外接显示器的亮度，也可以用夜间、日常、明亮三档预设一次调好所有屏幕。
- [风度](https://github.com/ZhaoOyu/fengdu) · 在配有风扇的 Apple 芯片 Mac 上查看芯片温度和风扇转速，手动指定转速或设置随温度提速的曲线。
