import Foundation

enum AppLanguage {
    static let choices = ["system", "zh-Hans", "en"]
    private static let testing = !Set(CommandLine.arguments).isDisjoint(with: ["--demo", "--ui-test", "--self-test"])
    private static var demoChoice = "system"
    static var choice: String {
        get {
            if testing { return demoChoice }
            let saved = UserDefaults.standard.string(forKey: "interfaceLanguage") ?? "system"
            return choices.contains(saved) ? saved : "system"
        }
        set {
            guard choices.contains(newValue) else { return }
            if testing { demoChoice = newValue }
            else { UserDefaults.standard.set(newValue, forKey: "interfaceLanguage") }
        }
    }
    static var english: Bool {
        let identifier = choice == "system" ? Locale.preferredLanguages.first ?? "en" : choice
        return !identifier.lowercased().hasPrefix("zh")
    }
    static var locale: Locale { Locale(identifier: english ? "en" : "zh-Hans") }
    static var names: [String] { [english ? "System default" : "跟随系统", "简体中文", "English"] }
}

// Fixed UI labels and fragments of hardware messages sent across process boundaries.
private let englishText: [String: String] = [
    "：": ": ",
    "，": ", ",
    "）": ")",
    "Codex 回复超出大小限制。": "The Codex response exceeded the size limit.",
    "Codex 连接已断开，请检查 CLI 和登录状态。": "Codex disconnected. Check your CLI and login.",
    "Codex 额度": "Codex Quota",
    "五小时": "5-hour",
    "刷新": "Refresh",
    "右侧倒计时": "Countdown",
    "图标额度": "Quota window",
    "圆环": "Ring",
    "圆环始终显示额度": "The ring always shows quota",
    "天": "d",
    "小时": "h",
    "待刷新": "Awaiting refresh",
    "显示倒计时": "Show countdown",
    "显示内容": "Show in menu bar",
    "显示额度数值": "Show quota value",
    "暂无重置时间": "Reset time unavailable",
    "更新于": "Updated at",
    "未找到 Codex CLI，请安装并运行 codex login。": "Codex CLI was not found. Install it and run codex login.",
    "未返回 Codex 额度，请检查 ChatGPT 登录状态。": "No Codex quota returned. Check your ChatGPT login.",
    "正在刷新额度…": "Updating quota…",
    "每 60 秒刷新": "Refreshes every 60 seconds",
    "每周": "Weekly",
    "演示": "Demo",
    "演示数据": "Demo data",
    "点击切换，至少保留一项": "Select at least one item",
    "用量页面": "Usage page",
    "登录系统时启动": "Open at login",
    "等待读取": "Waiting for quota",
    "菜单栏样式": "Menu bar style",
    "读取超时，请稍后刷新。": "The request timed out. Try refreshing later.",
    "账号未返回五小时或周额度。": "Your account did not return a five-hour or weekly quota.",
    "跑道": "Track",
    "退出": "Quit",
    "重置": " reset",
    "重置于": "Resets at",
    "重置倒计时": " reset countdown",
    "额度剩余": " quota remaining",
    "额度读取失败，请检查 Codex 登录状态。": "Could not read quota. Check your Codex login.",
]
private let fragments = try! NSRegularExpression(pattern: englishText.keys
    .sorted { $0.count > $1.count }.map(NSRegularExpression.escapedPattern(for:)).joined(separator: "|"))

func tr(_ text: String) -> String {
    guard AppLanguage.english else { return text }
    if let value = englishText[text] { return value }
    let source = text as NSString
    let matches = fragments.matches(in: text, range: NSRange(location: 0, length: source.length))
    guard !matches.isEmpty else { return text }
    let result = NSMutableString(string: text)
    for m in matches.reversed() {
        if let translated = englishText[source.substring(with: m.range)] {
            result.replaceCharacters(in: m.range, with: translated)
        }
    }
    return result as String
}
