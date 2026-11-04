# Codex 余量 0.1.11

- 新增可选 GNOME 扩展（45–50）：左键直接展开原生额度面板，支持额度、倒计时、样式、语言及登录启动等控制。
- 跑道使用原生文字与主题颜色绘制，不再受 AppIndicator 宽图像布局限制。
- 扩展连接成功后隐藏旧托盘；禁用或断开后恢复旧托盘。主程序与凭据读取逻辑不变。
- DEB 内置扩展，另提供独立 `.shell-extension.zip`。安装不会自动启用扩展或重启桌面。
- GNOME 50 完成隔离 Wayland 原生面板测试；45–49 尚未逐版本实机验证。GNOME 42–44 保留原菜单，macOS 不变。

退出旧版、安装新版并重新打开应用，然后启用：

```bash
gnome-extensions enable codex-quota-bar@zhaooyu.github.io
```

若提示找不到扩展，保存工作后注销并重新登录再执行。DEB 用户无需重复安装 ZIP。

Adds an optional native GNOME 45–50 quota panel with theme-aware track rendering, direct controls and automatic tray fallback. Bundled in the DEB and also available as a standalone extension ZIP. Requires the running v0.1.11+ app. Installation does not enable the extension automatically. GNOME 50 was runtime-tested; older supported versions were not individually tested. macOS is unchanged.

[中文使用指南](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.11/README.md) · [English guide](https://github.com/ZhaoOyu/codex-quota-bar/blob/v0.1.11/README.en.md)
