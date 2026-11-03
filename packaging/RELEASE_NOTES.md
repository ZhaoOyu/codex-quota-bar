**v0.1.6 新增跑道显示。** 菜单栏空间紧张时，可以只留一个额度数字，也可以只看距离重置还有多久。

- 圆环始终显示额度，旁边的倒计时可以隐藏。切换到跑道后，点击两块预览即可选择数值、倒计时或两者同时显示。
- 每种样式都会记住选择。五小时的 H、每周的 W 与额度数字同样大，切换样式也能轻松辨认。
- Mac 使用 Swift 原生面板，设置按钮等宽排列。Ubuntu 用户也能使用跑道和显示预览开关。

## 选择你的下载

| 你的电脑 | 安装包 |
| --- | --- |
| Mac · Apple Silicon（M 系列芯片） | [下载 Apple Silicon 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.6/codex-quota-bar-macos-arm64.zip) |
| Mac · Intel 芯片 | [下载 Intel 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.6/codex-quota-bar-macos-x86_64.zip) |
| Ubuntu 22.04 及以上 | [下载 Ubuntu 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.6/codex-quota-bar_0.1.6_all.deb) |

## 几步开始使用

**准备登录：**应用沿用本机 [Codex CLI](https://developers.openai.com/codex/cli) 的 ChatGPT 登录状态，无需配置 API Key。首次使用前，请安装 Codex CLI，并在终端运行 `codex login`、选择 ChatGPT 账号登录。仅使用 API Key 的登录方式不提供本工具所需的套餐额度。

**macOS：**解压 ZIP，将 **Codex Quota Bar.app** 拖入“应用程序”，双击打开后点击菜单栏图标即可。无需另外安装 Python。

当前 macOS 安装包尚未进行 Developer ID 签名或公证。如果系统阻止打开，请先核验 [SHA256 校验文件](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.6/SHA256SUMS.txt)，再到“系统设置 → 隐私与安全性”批准打开。

**Ubuntu：**在下载目录打开终端，运行：

```bash
sudo apt install ./codex-quota-bar_0.1.6_all.deb
```

然后从应用列表打开 **Codex Quota Bar**。GNOME 桌面需启用 **Ubuntu AppIndicators** 扩展；点击顶部图标，选择“打开额度面板”。支持的桌面也可中键直接打开。

**从旧版本升级：**先退出正在运行的应用，再替换 macOS 应用或安装新的 Ubuntu 安装包，完成后重新打开。

## 日常使用的小提示

额度约每分钟自动刷新，也可以手动点击“刷新”。在面板中开启“登录系统时启动”，下次登录桌面后即可继续查看。

`--` 表示暂无对应数据，`待刷新` 表示已到重置时间、正在等待新数据。账户未提供五小时额度时，详情面板会隐藏该区域。

工具只读取额度，不发送提示词、不触发模型推理，也不另行保存或输出账号令牌。

[查看完整使用指南](https://github.com/ZhaoOyu/codex-quota-bar#readme) · [反馈问题](https://github.com/ZhaoOyu/codex-quota-bar/issues)

这是独立开源工具，与 OpenAI 无隶属关系。
