# Codex 余量 0.1.10

修正 Ubuntu 跑道位置：

- 跑道重新包围额度和倒计时，不再显示为文字左侧的空心小图标。
- 使用原生文本排版计算宽度及居中位置，支持中文倒计时；宽图像采用明确的浅色，适配 Ubuntu 默认深色顶栏，不依赖符号图标着色。
- 保留 v0.1.8 的点击直接展开控制菜单；Mac 界面与原有设置不变。
- 安装包推荐安装中文字体，避免精简 Ubuntu 环境出现缺字方框。

Ubuntu track mode once again encloses its quota/countdown text. Native text measurement keeps CJK readings centered. Wide images use an explicit light foreground for the stock dark panel, instead of relying on symbolic tinting. The direct control menu from v0.1.8 remains available. macOS behavior is unchanged.

退出旧版后，安装新版 Ubuntu DEB 即可覆盖升级，无需先卸载。

[中文使用指南](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.10/README.md) · [English guide](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.10/README.en.md)
