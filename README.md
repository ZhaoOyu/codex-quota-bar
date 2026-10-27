# Codex Quota Bar

让 Codex 剩余额度常驻 **Ubuntu 顶部面板 / macOS 菜单栏**。

```text
5h 78% · W 62% · 02:34
│        │       └─ 五小时窗口距离结束还有 2 小时 34 分钟
│        └───────── 周剩余额度
└────────────────── 五小时剩余额度
```

上面是显示示例。实际数据来自本机已登录的 Codex CLI。

- 同时显示账号返回的额度；没有五小时窗口时仅显示周余量，隐藏五小时余量和结束时间。
- 菜单信息使用正常文字颜色，浅色主题为黑色，深色主题跟随系统，不再显示为禁用的灰色。
- 每 60 秒刷新额度，每秒更新倒计时；支持手动刷新。
- 原生菜单栏 / AppIndicator，无浏览器窗口，无 Electron。
- 支持登录系统时启动，默认关闭，由菜单显式开启。
- 断网或登录失效时显示错误；不把未知额度当作 100%。
- 不保存、不输出账号令牌，不发送提示词，不触发模型推理。

## 准备 Codex 登录

需要当前版本的 [Codex CLI](https://developers.openai.com/codex/cli)，并使用 ChatGPT 账号登录：

```bash
npm install -g @openai/codex
codex login
```

纯 API Key 登录不提供 ChatGPT 套餐额度。账户必须返回 300 分钟或 10080 分钟窗口；其他窗口不会被误标为“五小时”或“周”。未返回五小时窗口时隐藏对应信息，例如只有周额度时状态栏显示 `W 62%`；已返回五小时窗口但余量为 0% 时仍显示。周额度未提供时显示 `--`。

## Ubuntu 安装

目标环境为 Ubuntu 22.04 及以上、Python 3.10 及以上、GNOME + AppIndicator。

从仓库的 Releases 页面下载 `.deb` 后安装：

```bash
sudo apt install ./codex-quota-bar_0.1.2_all.deb
codex-quota-bar
```

也可以在应用列表中打开 **Codex Quota Bar**。安装包会依赖系统 GTK / Ayatana 组件，并建议安装 GNOME AppIndicator 扩展。若顶部没有图标，在“扩展”应用中启用 **Ubuntu AppIndicators**，然后重新登录桌面。非 GNOME 桌面对文本标签的支持可能不同。

从源码运行：

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 gnome-shell-extension-appindicator
/usr/bin/python3 -m codex_quota_bar
```

Ubuntu 请用系统 Python；普通虚拟环境通常不能导入 apt 安装的 `gi`。如需虚拟环境，请用 `python3 -m venv --system-site-packages .venv`。

## macOS 安装

从 Releases 下载对应架构的 ZIP：Apple Silicon 选 `arm64`，Intel 选 `x86_64`。解压后拖到“应用程序”，再双击启动。没有 Dock 图标，所有操作位于顶部菜单栏。预构建包分别在 macOS 14 / macOS 15 Intel 上构建，更早系统请从源码运行并自行验证兼容性。

当前构建未使用 Apple Developer ID 签名或公证。如果 macOS 阻止打开，请先核验 Release 附带的 SHA256SUMS，再在“系统设置 → 隐私与安全性”批准此应用。不要关闭系统全局安全检查。

从源码运行（Python 3.10+）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m codex_quota_bar
```

Finder 不继承终端 PATH。应用会检查 PATH、Homebrew、`~/.npm-global/bin`、`~/.local/bin`、Volta、nvm 和 Codex.app 的常见路径，并为 Codex 子进程补充 Node 搜索路径。自定义 CLI 路径可使用：

```bash
python3 -m codex_quota_bar --codex /absolute/path/to/codex
# 或
CODEX_QUOTA_CODEX_BIN=/absolute/path/to/codex python3 -m codex_quota_bar
```

对于 nvm，优先使用当前 PATH；PATH 没有 Codex 时才按版本从新到旧查找已安装的 CLI。如果需要固定版本，可通过 `--codex` 指定。

若双击启动一直显示“断开”，先退出状态栏应用，再从已能运行 Codex 的终端启动，以确认是否属于 GUI 环境差异：

```bash
"/Applications/Codex Quota Bar.app/Contents/MacOS/Codex Quota Bar" --codex "$(command -v codex)"
```

若仍失败，请检查 `codex --version`、`codex login status`，并在终端运行 `codex app-server` 查看启动错误。服务正常时会等待输入，可按 Ctrl+C 退出。应用仅显示经过分类的错误提示，不输出服务端原始日志。

## 状态说明

| 显示 | 含义 |
| --- | --- |
| `5h 78% · W 62% · 02:34` | 两个剩余百分比，和五小时结束倒计时（小时:分钟） |
| `--` / `--:--` | 接口未提供该额度 / 时间 |
| `待刷新` | 已超过服务器提供的重置时间，等待重新查询；不会自动显示 100% |
| `Codex !` | 无法读取，点击菜单查看错误；60 秒后重试 |
| `! 5h …` | 上次成功数据已超过 3 分钟，可能已过期 |
| `[演示] …` | `--demo` 的固定示例，绝非真实账号额度 |

百分比向下取整，倒计时分钟向上取整。应用每次刷新启动短生命周期的 `codex app-server` 子进程，通过 stdio 完成初始化并调用 `account/rateLimits/read`，随后关闭进程。网络操作在后台线程运行，不阻塞菜单。

当请求失败时清空之前的额度，避免切换账号后显示旧账号数据。应用自身不读写认证文件；Codex CLI 仍按其自身配置访问网络、登录凭据和本地运行目录。需确保 Codex 的用户目录可写。

接口参考：[OpenAI Codex App Server — Rate limits](https://learn.chatgpt.com/docs/app-server)。这是独立开源工具，与 OpenAI 无隶属关系。

## 检查与开发

```bash
python3 -m codex_quota_bar --once           # 读取真实数据，不启动界面
python3 -m codex_quota_bar --once --json    # 输出额度 JSON，无令牌
python3 -m codex_quota_bar --demo           # 菜单栏演示
python3 -m unittest discover -s tests -v    # 无需账号和网络
python3 scripts/build_deb.py               # 输出 dist/*.deb
```

macOS 本机打包：

```bash
python -m pip install . pyinstaller==6.22.3
python -m PyInstaller --noconfirm packaging/macos.spec
```

测试覆盖窗口识别、余量换算、倒计时边界、数据缺失、错误脱敏、真实子进程 JSON-RPC 握手、超时清理、后台状态恢复与开机启动文件。CI 还会启动两种原生界面及打包后的应用，运行三秒后退出。演示模式不能证明真实账号连接成功；应在自己的桌面上额外运行一次 `--once`。

## 卸载

先在菜单关闭“登录系统时启动”，然后退出。Ubuntu 使用 `sudo apt remove codex-quota-bar`；macOS 删除应用即可。若应用已删除，可手动删除自己用户目录中的 `~/.config/autostart/codex-quota-bar.desktop` 或 `~/Library/LaunchAgents/io.github.codex-quota-bar.plist`。

MIT License.

---

**English:** A lightweight native menu-bar utility for macOS and Ubuntu. Shows remaining Codex five-hour and weekly quotas, with a countdown to the five-hour reset. Requires the Codex CLI signed in with a ChatGPT account. Polls the official app-server rate-limit RPC once per minute; performs no inference and stores no tokens. See Releases for Ubuntu DEB and macOS Apple Silicon / Intel builds. macOS builds are currently unsigned and not notarized.
