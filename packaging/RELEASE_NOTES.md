## v0.1.5：统一 macOS 与 Ubuntu 原生界面

- 加粗额度圆环，中央显示剩余数值（省略百分号），底部以 H / W 标识五小时 / 周额度；右侧用 `·` 连接重置倒计时。
- macOS 使用 AppKit 原生详情面板；Ubuntu 使用 GTK 原生面板及可随主题着色的 symbolic 图标，统一信息布局和垂直居中。
- “图标额度”和“右侧倒计时”分别提供横向排列的“每周 / 五小时”按钮，独立切换并保存选择。
- 正常启动读取真实 Codex 额度。缺失、过期和查询失败状态不会伪装成有效额度；演示模式始终带有标记。
- 修复 macOS 打包应用因偏好设置初始化方式不正确而无法启动的问题，保留原有显示选择。

## 安装

- **Ubuntu 22.04+**：下载 `codex-quota-bar_0.1.5_all.deb`，运行 `sudo apt install ./codex-quota-bar_0.1.5_all.deb`。GNOME 需启用 Ubuntu AppIndicators 扩展；点击托盘后选择“打开额度面板”，支持的桌面也可中键打开。
- **macOS Apple Silicon**：下载 `codex-quota-bar-macos-arm64.zip`。
- **macOS Intel**：下载 `codex-quota-bar-macos-x86_64.zip`。
- macOS 解压后将应用移入“应用程序”。当前构建未使用 Developer ID 签名或公证；请核验 `SHA256SUMS.txt`，如被系统阻止，在“系统设置 → 隐私与安全性”批准打开。
- 使用前安装 Codex CLI，并通过 `codex login` 登录 ChatGPT 账号。应用每次查询完成后等待 60 秒刷新，每秒更新倒计时，不发送提示词、不触发模型推理。

Ubuntu 的字体、托盘尺寸和间距由桌面主题及 AppIndicator 扩展决定；详情面板不使用 macOS 的半透明材质。完整说明见仓库 README。

**English:** Native quota rings and configurable detail panels for both macOS and Ubuntu, with independent weekly/five-hour selectors and persistent preferences. This release also fixes a macOS bundle-only startup crash. Choose the matching macOS architecture or install the Ubuntu DEB; verify the included SHA256 checksums. Requires the Codex CLI signed in with a ChatGPT account. macOS builds are not Developer ID signed or notarized.

这是独立开源工具，与 OpenAI 无隶属关系。 / This is an independent open-source utility, not an official OpenAI product.
