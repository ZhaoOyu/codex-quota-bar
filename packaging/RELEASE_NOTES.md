剩余额度和重置时间，就在你抬眼能看到的地方。

**v0.1.5 带来全新的额度圆环和更顺手的详情面板。** 开始一轮重构前看余量，安排下一段工作时看倒计时，让每一次使用 Codex 都更心中有数。

![菜单栏中的额度圆环与重置倒计时](https://raw.githubusercontent.com/ZhaoOyu/codex-quota-bar/v0.1.5/docs/images/macos-menubar.png)

*图片为演示数据，实际使用时显示你的账户额度。*

## 新版亮点

- **余量一眼看清。** 加粗圆环展示剩余比例，中央显示数值，底部 `H` / `W` 区分五小时与周额度；重置倒计时紧挨圆环，方便随时查看。
- **你关心什么，就显示什么。** “图标额度”和“右侧倒计时”可以分别选择每周或五小时。例如圆环看周余量，右侧看五小时何时重置。点一下切换，下次打开仍会记住。
- **macOS 和 Ubuntu，同样顺手。** 两个平台都能在原生详情面板中查看额度、进度条和重置时间，适配系统明暗外观。
- **修复 Mac 启动问题。** 解决了 macOS 应用启动时可能出现的崩溃。

## 选择你的下载

| 你的电脑 | 安装包 |
| --- | --- |
| Mac · Apple Silicon（M 系列芯片） | [下载 Apple Silicon 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.5/codex-quota-bar-macos-arm64.zip) |
| Mac · Intel 芯片 | [下载 Intel 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.5/codex-quota-bar-macos-x86_64.zip) |
| Ubuntu 22.04 及以上 | [下载 Ubuntu 版](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.5/codex-quota-bar_0.1.5_all.deb) |

## 几步开始使用

**准备登录：**应用沿用本机 [Codex CLI](https://developers.openai.com/codex/cli) 的 ChatGPT 登录状态，无需配置 API Key。首次使用前，请安装 Codex CLI，并在终端运行 `codex login`、选择 ChatGPT 账号登录。仅使用 API Key 的登录方式不提供本工具所需的套餐额度。

**macOS：**解压 ZIP，将 **Codex Quota Bar.app** 拖入“应用程序”，双击打开后点击菜单栏图标即可。无需另外安装 Python。

当前 macOS 安装包尚未进行 Developer ID 签名或公证。如果系统阻止打开，请先核验 [SHA256 校验文件](https://github.com/ZhaoOyu/codex-quota-bar/releases/download/v0.1.5/SHA256SUMS.txt)，再到“系统设置 → 隐私与安全性”批准打开。

**Ubuntu：**在下载目录打开终端，运行：

```bash
sudo apt install ./codex-quota-bar_0.1.5_all.deb
```

然后从应用列表打开 **Codex Quota Bar**。GNOME 桌面需启用 **Ubuntu AppIndicators** 扩展；点击顶部图标，选择“打开额度面板”。支持的桌面也可中键直接打开。

**从旧版本升级：**先退出正在运行的应用，再替换 macOS 应用或安装新的 Ubuntu 安装包，完成后重新打开。

## 日常使用的小提示

额度约每分钟自动刷新，也可以手动点击“刷新”。在面板中开启“登录系统时启动”，下次登录桌面后即可继续查看。

`--` 表示暂无对应数据，`待刷新` 表示已到重置时间、正在等待新数据。账户未提供五小时额度时，详情面板会隐藏该区域。

工具只读取额度，不发送提示词、不触发模型推理，也不另行保存或输出账号令牌。

[查看完整使用指南](https://github.com/ZhaoOyu/codex-quota-bar#readme) · [反馈问题](https://github.com/ZhaoOyu/codex-quota-bar/issues)

这是独立开源工具，与 OpenAI 无隶属关系。
