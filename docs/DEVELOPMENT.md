# 源码运行与开发

日常安装和使用请查看 [README](../README.md)。本文保留源码运行、排查、打包与数据规则，供需要进一步配置或参与开发的用户参考。

## 从源码运行

需要 Python 3.10+ 和已通过 ChatGPT 账号登录的 Codex CLI。

```bash
git clone https://github.com/ZhaoOyu/codex-quota-bar.git
cd codex-quota-bar
```

### macOS

原生界面使用 AppKit / PyObjC，源码要求 macOS 11+；已验证环境见 [VALIDATION.md](../VALIDATION.md)，较早系统仍需自行验证。

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m codex_quota_bar
```

如果默认 `python3` 指向旧版 Anaconda，请用已安装的 Python 3.10+ 创建环境，例如 Apple Silicon 上的 `/opt/homebrew/bin/python3 -m venv .venv`。后续使用 `.venv/bin/python`，避免混用解释器。

### Ubuntu

```bash
sudo apt install python3-gi python3-cairo librsvg2-common gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 gnome-shell-extension-appindicator
/usr/bin/python3 -m codex_quota_bar
```

请使用系统 Python；普通虚拟环境通常无法导入 apt 安装的 `gi`。需要虚拟环境时使用 `python3 -m venv --system-site-packages .venv`。

Ubuntu 使用 GTK / Ayatana AppIndicator。详情面板通过托盘菜单打开，支持的桌面可用中键；新版 Ayatana 提供主激活信号时也连接该事件。字体、托盘尺寸与间距由宿主桌面决定；Wayland 下窗口位置由合成器控制。

## 找不到 Codex 或无法读取额度

先检查：

```bash
codex --version
codex login status
```

Finder 不继承终端 PATH。应用会检查 PATH、Homebrew、`~/.npm-global/bin`、`~/.local/bin`、Volta、nvm 和 Codex.app 的常见位置，并为 Codex 子进程补充 Node 搜索路径。nvm 优先使用当前 PATH，未找到时再按版本从新到旧查找。

自定义 CLI 路径：

```bash
python -m codex_quota_bar --codex /absolute/path/to/codex
# 或
CODEX_QUOTA_CODEX_BIN=/absolute/path/to/codex python -m codex_quota_bar
```

macOS 安装包可先退出，再从已能运行 Codex 的终端启动：

```bash
"/Applications/Codex Quota Bar.app/Contents/MacOS/Codex Quota Bar" --codex "$(command -v codex)"
```

也可运行 `codex app-server` 查看启动错误。正常启动时会等待输入，可按 Ctrl+C 退出。应用仅显示分类后的错误提示，不输出服务端原始日志。

## 数据规则与实现

- 通过短生命周期的 `codex app-server` 子进程，以 stdio 完成初始化并调用 `account/rateLimits/read`，随后关闭进程。查询在后台线程中进行。
- 每次查询完成后等待 60 秒刷新，每秒更新倒计时。
- 只把服务器返回的 300 / 10080 分钟窗口标为五小时 / 周额度，不按套餐名或字段顺序推测。
- 剩余比例向下取整；倒计时分钟向上取整。周倒计时超过 24 小时显示天和小时，省略不足一小时的部分；否则显示小时与分钟。
- 已到重置时间时显示“待刷新”，不推测额度恢复。请求失败后清空旧额度，避免账号切换后保留旧账号数据；上次成功数据超过 3 分钟时标记过期。
- 手动选定窗口后，即使该窗口缺失也保留选择并显示未知值。未选择时优先使用可用的五小时窗口，否则使用周窗口。
- 应用自身不读写认证文件。Codex CLI 仍按其自身配置访问网络、登录凭据和运行目录，因此需确保其用户目录可写。

macOS 使用模板图像与原生控件。Ubuntu 圆环使用可主题化的 SVG，并将系统字体转为路径，避免 GTK symbolic 加载器丢失文字或把圆环中心填实。

## 检查与测试

```bash
python -m codex_quota_bar --once              # 真实额度，不启动界面
python -m codex_quota_bar --once --json       # 额度 JSON，无令牌
python -m codex_quota_bar --demo              # 明确标记的演示数据
python -m codex_quota_bar --demo --smoke-test # 展开原生面板，3 秒后退出
python -m unittest discover -s tests -v
```

测试无需账号和网络。AppKit 测试需要 macOS 桌面会话，GTK 测试需要 Linux 图形会话；不适用的原生测试会跳过。Ubuntu 无显示环境时，先安装 `xvfb dbus-x11`，再运行：

```bash
dbus-run-session -- xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v
```

测试涵盖额度解析、倒计时、错误脱敏、子进程 JSON-RPC、超时清理、后台状态恢复、启动配置、独立按钮选择、偏好保存和 symbolic 图标渲染。

## 打包与发布

macOS：

```bash
python -m pip install . pyinstaller==6.22.3
python -m PyInstaller --noconfirm packaging/macos.spec
```

Ubuntu：

```bash
python3 scripts/build_deb.py
```

产物位于 `dist/`。[GitHub Actions](https://github.com/ZhaoOyu/codex-quota-bar/actions) 会测试 Ubuntu、macOS Apple Silicon 和 Intel，验证打包后启动及精简 PATH 下的 RPC。推送 `v*` 标签后，三个平台全部通过才发布安装包和 SHA256 校验文件。

发布前同步 `codex_quota_bar/__init__.py`、`pyproject.toml`、`packaging/macos.spec` 中的版本号，以及 README 的下载链接和 `packaging/RELEASE_NOTES.md`。演示模式不能证明真实账户连接成功，应在已登录的桌面上另行检查 `--once` 和面板显示。验证记录见 [VALIDATION.md](../VALIDATION.md)。

## 配置清理

先关闭“登录系统时启动”并退出应用。若应用已删除，可手动移除当前用户的启动配置：

- Ubuntu：`~/.config/autostart/codex-quota-bar.desktop`
- macOS：`~/Library/LaunchAgents/io.github.codex-quota-bar.plist`

Ubuntu 的显示选择保存在 `~/.config/codex-quota-bar/preferences.json`；设置 `XDG_CONFIG_HOME` 时使用对应目录。删除该文件即可重置选择。

macOS 的显示选择保存在 `io.github.codex-quota-bar` 偏好域：

```bash
defaults delete io.github.codex-quota-bar
```
