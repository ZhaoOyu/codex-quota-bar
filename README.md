# Codex Quota Bar

让 Codex 剩余额度常驻 **macOS 菜单栏 / Ubuntu 顶部面板**。数据来自本机已登录的 Codex CLI，无需 API Key，不发送提示词、不触发模型推理。

## macOS 原生圆环界面

![macOS 菜单栏演示](docs/images/macos-menubar.png)

- **额度圆环**：圆环表示剩余额度，中央显示数值（省略 `%`），底部 `H` 表示五小时额度、`W` 表示周额度。圆环和文字加粗，自动适配系统明暗外观。
- **右侧倒计时**：用 `·` 连接圆环与重置倒计时，直接显示时间文字。
- **原生详情面板**：点击菜单栏图标查看账号返回的额度、进度条、重置时间和刷新状态。使用 AppKit 系统控件与半透明材质，无浏览器窗口、无 Electron、无 Dock 图标。
- **独立选择**：“图标额度”和“右侧倒计时”各占一行，标签后并排显示 **每周 / 五小时** 两个按钮。点击直接选择，选中状态互斥；两项设置互不影响，自动保存。

<img src="docs/images/macos-panel.png" alt="macOS 原生详情面板演示" width="340">

以上为**演示数据的原生组件渲染**，不是账户截图；实际面板的半透明效果取决于系统外观和桌面背景。当前 macOS 圆环界面请从源码运行，历史 Release 安装包的界面以相应版本说明为准。

首次使用会优先选择可用的五小时窗口，否则选择周窗口。手动选择后不再自动切换：例如账号只返回周额度，但选择了“五小时”，对应位置会显示未知值，而不会替换成周额度。详情面板只在账号返回五小时窗口时显示该区域。

## 功能与数据规则

- 每次查询完成后等待 60 秒自动刷新；每秒更新倒计时，也可手动刷新。
- 支持登录系统时启动，默认关闭，在面板或菜单中开启。
- 只把服务器返回的 **300 分钟 / 10080 分钟** 窗口标为五小时 / 周额度，不按套餐名或字段顺序推测。
- 数值表示**剩余比例**，向下取整；有数据的 `0` 表示额度耗尽，未知数据不会显示成 `0` 或 `100`。
- 倒计时分钟向上取整。周倒计时超过 24 小时显示天和小时，省略不足一小时的部分；否则显示 `小时:分钟`。五小时倒计时使用 `小时:分钟`。
- 重置时间已到时显示“待刷新”，等待服务器返回新数据，不自动假定额度恢复。
- 请求失败后清空旧额度，避免切换账号后继续显示旧账号数据；上次成功数据超过 3 分钟时标记过期。
- 不保存、不输出账号令牌。显示偏好保存在 macOS 用户偏好设置中，开机启动配置保存在当前用户目录中。

## 准备 Codex 登录

需要 [Codex CLI](https://developers.openai.com/codex/cli)，并使用 ChatGPT 账号登录：

```bash
npm install -g @openai/codex
codex login
```

纯 API Key 登录不提供此工具需要的 ChatGPT 套餐额度。登录完成后可先运行 `python -m codex_quota_bar --once` 检查连接。

## macOS 安装与运行

当前原生界面需要 **macOS 11+、Python 3.10+**。本地已验证环境见 [VALIDATION.md](VALIDATION.md)；较早系统版本仍需自行验证。

从源码运行：

```bash
git clone https://github.com/ZhaoOyu/codex-quota-bar.git
cd codex-quota-bar
python3 --version  # 确认是 3.10 或更新版本
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m codex_quota_bar
```

如果默认 `python3` 指向旧版 Anaconda，请使用已安装的 Python 3.10+ 创建虚拟环境，例如 Apple Silicon 上的 `/opt/homebrew/bin/python3 -m venv .venv`。后续运行项目时使用 `.venv/bin/python`，避免混用解释器。

普通启动读取真实数据；`python -m codex_quota_bar --demo` 使用明确标记的固定演示数据。

### 预构建安装包

[Releases](https://github.com/ZhaoOyu/codex-quota-bar/releases) 提供历史版本安装包。Apple Silicon 选 `arm64` ZIP，Intel 选 `x86_64` ZIP；解压后拖到“应用程序”，再双击启动。仓库最新源码的界面改动不一定已包含在已发布安装包中。

预构建包在 macOS 14 / macOS 15 Intel 上构建。当前构建未使用 Apple Developer ID 签名或公证；若系统阻止打开，请先核验 Release 附带的 SHA256SUMS，再在“系统设置 → 隐私与安全性”批准此应用，不要关闭全局安全检查。

### 找不到 Codex 或无法读取额度

Finder 不继承终端 PATH。应用会检查 PATH、Homebrew、`~/.npm-global/bin`、`~/.local/bin`、Volta、nvm 和 Codex.app 的常见位置，并为 Codex 子进程补充 Node 搜索路径。

自定义 CLI 路径：

```bash
python -m codex_quota_bar --codex /absolute/path/to/codex
# 或
CODEX_QUOTA_CODEX_BIN=/absolute/path/to/codex python -m codex_quota_bar
```

nvm 优先使用当前 PATH；没有找到 Codex 时才按版本从新到旧查找。需要固定版本时请使用 `--codex`。

若应用无法读取，先退出菜单栏应用，再从已能运行 Codex 的终端启动：

```bash
"/Applications/Codex Quota Bar.app/Contents/MacOS/Codex Quota Bar" --codex "$(command -v codex)"
```

也可检查 `codex --version`、`codex login status`，并运行 `codex app-server` 查看启动错误。服务正常时会等待输入，可按 Ctrl+C 退出。应用仅显示分类后的错误提示，不输出服务端原始日志。

## Ubuntu 安装与运行

目标环境：Ubuntu 22.04+、Python 3.10+、GNOME + AppIndicator。Ubuntu 和命令行保持文字显示，不使用 macOS 圆环界面：

```text
5h 78% · W 62% · 02:34
│        │       └─ 五小时窗口距离重置还有 2 小时 34 分钟
│        └───────── 周剩余额度
└────────────────── 五小时剩余额度
```

没有五小时窗口时隐藏相关信息，显示周额度及其倒计时，例如 `W 62% · 3天3小时`。周额度未提供时显示 `--`。

从 [Releases](https://github.com/ZhaoOyu/codex-quota-bar/releases) 下载 `.deb` 后安装，例如：

```bash
sudo apt install ./codex-quota-bar_0.1.4_all.deb
codex-quota-bar
```

也可以在应用列表中打开 **Codex Quota Bar**。安装包依赖系统 GTK / Ayatana 组件，并建议安装 GNOME AppIndicator 扩展。若顶部没有图标，在“扩展”应用中启用 **Ubuntu AppIndicators**，再重新登录桌面。非 GNOME 桌面对文本标签的支持可能不同。

从源码运行（先克隆仓库并进入目录）：

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 gnome-shell-extension-appindicator
/usr/bin/python3 -m codex_quota_bar
```

Ubuntu 请用系统 Python；普通虚拟环境通常无法导入 apt 安装的 `gi`。需要虚拟环境时，请使用 `python3 -m venv --system-site-packages .venv`。

## 状态说明

| 状态 | macOS 圆环界面 | Ubuntu / 命令行 |
| --- | --- | --- |
| 正常 | 圆环内数值 + 底部 `H/W`，右侧为所选窗口倒计时 | `5h 78% · W 62% · 02:34` |
| 未返回所选额度 | 虚线圆环、`--` | 对应值为 `--`，缺失的五小时窗口隐藏 |
| 未返回重置时间 | `--:--` | `--:--` |
| 重置时间已到 | 虚线圆环、`--`，所选倒计时为“待刷新” | 对应数值和倒计时为“待刷新” |
| 查询失败 | 清空额度、显示 `!`，面板内有错误提示 | `Codex !`，菜单内有错误提示 |
| 数据超过 3 分钟未更新 | 倒计时前显示 `!`，面板提示过期 | 标题前显示 `!` |
| 演示模式 | 菜单栏和面板带“演示”标记 | 标题带 `[演示]` |

应用每次刷新启动短生命周期的 `codex app-server` 子进程，通过 stdio 完成初始化并调用 `account/rateLimits/read`，随后关闭进程。网络操作在后台线程中运行，不阻塞界面。

应用自身不读写认证文件；Codex CLI 仍按其自身配置访问网络、登录凭据和本地运行目录，需要确保其用户目录可写。

这是独立开源工具，与 OpenAI 无隶属关系。

## 检查与开发

在已安装依赖的 Python 环境中运行：

```bash
python -m codex_quota_bar --once           # 读取真实数据，不启动界面
python -m codex_quota_bar --once --json    # 输出额度 JSON，无令牌
python -m codex_quota_bar --demo           # 原生界面演示
python -m codex_quota_bar --demo --smoke-test  # 展开 macOS 面板，3 秒后退出
python -m unittest discover -s tests -v
```

测试无需账号和网络。macOS 的 AppKit 测试需要可用的桌面会话；Linux 自动跳过这部分测试。测试覆盖额度解析、倒计时、错误脱敏、真实子进程 JSON-RPC、超时清理、后台状态恢复、启动配置，以及原生按钮直接选择、选中状态与偏好保存。

macOS 本机打包：

```bash
python -m pip install . pyinstaller==6.22.3
python -m PyInstaller --noconfirm packaging/macos.spec
```

Ubuntu 打包：

```bash
python3 scripts/build_deb.py  # 输出 dist/*.deb
```

[GitHub Actions](https://github.com/ZhaoOyu/codex-quota-bar/actions) 会运行测试、原生界面启动检查、安装包构建和打包后验证。演示模式不能证明真实账户连接成功，发布前应在已登录的桌面上额外运行 `--once` 并检查界面。当前及历史验证记录见 [VALIDATION.md](VALIDATION.md)。

## 卸载

先关闭“登录系统时启动”，再退出应用。Ubuntu 使用 `sudo apt remove codex-quota-bar`；macOS 删除应用即可。

若应用已删除，可手动移除当前用户的启动配置：

- Ubuntu：`~/.config/autostart/codex-quota-bar.desktop`
- macOS：`~/Library/LaunchAgents/io.github.codex-quota-bar.plist`

macOS 的显示选择保存在 `io.github.codex-quota-bar` 偏好域。需要同时清除选择时，退出应用后运行：

```bash
defaults delete io.github.codex-quota-bar
```

[MIT License](LICENSE).

---

**English:** A lightweight native quota monitor for macOS and Ubuntu. On macOS, a bold quota ring shows a remaining value with an H/W marker and a reset countdown; a native popover provides details and independent weekly/five-hour selection buttons. Ubuntu retains its text indicator. Requires the Codex CLI signed in with a ChatGPT account. Performs no inference and stores no account tokens. The new macOS UI is available from source; historical Releases may have an earlier interface. macOS packages are unsigned and not notarized.
