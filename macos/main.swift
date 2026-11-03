import SwiftUI
import AppKit

let args = CommandLine.arguments
let demo = args.contains("--demo")
let cli = args.firstIndex(of: "--codex").flatMap { args.indices.contains($0+1) ? args[$0+1] : nil } ??
    args.first(where: { $0.hasPrefix("--codex=") }).map { String($0.dropFirst(8)) }
let demoSuite = "quota.demo."+UUID().uuidString
let windows = ["weekly", "five_hour"]
func title(_ key: String) -> String { key == "weekly" ? tr("每周") : tr("五小时") }

final class QuotaApp: NSObject, NSApplicationDelegate, ObservableObject {
    let panel = MenuPanel()
    let prefs = Indicators(defaults: demo ? UserDefaults(suiteName: demoSuite)! : .standard)
    var login: LoginItem { LoginItem(identifier: "io.github.codex-quota-bar", arguments: (cli ?? ProcessInfo.processInfo.environment["CODEX_QUOTA_CODEX_BIN"]).map { ["--codex", $0] } ?? []) }
    var quota: Quota? = demo ? .example() : nil
    var next = Date.distantPast, busy = false, error = ""
    var timer: Timer?
    var lastIcon: ImageKey?
    struct ImageKey: Equatable {
        let ring: Bool, digits: String, marker: String, time: String, parts: Int, fraction: Double?
    }
    var stale: Bool { quota.map { !demo && Date().timeIntervalSince1970 - $0.fetched_at > 180 } ?? false }
    func choice(_ key: String) -> String {
        if let saved = prefs.defaults.string(forKey: key), windows.contains(saved) { return saved }
        return quota?.five_hour == nil ? "weekly" : "five_hour"
    }
    func window(_ key: String) -> Window? { key == "weekly" ? quota?.weekly : quota?.five_hour }
    var quotaKey: String { choice("quotaWindow") }
    var timeKey: String { choice("countdownWindow") }
    var digits: String { window(quotaKey)?.digits ?? "--" }
    var marker: String { quotaKey == "weekly" ? "W" : "H" }
    var time: String { tr(window(timeKey)?.countdown(weekly: timeKey == "weekly") ?? "--:--") }
    func applicationDidFinishLaunching(_ notification: Notification) {
        panel.configure(QuotaView(model: self))
        tick()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in self?.tick() }
        if args.contains("--smoke-test") {
            setLanguage("en")
            precondition(panel.item.button?.toolTip?.hasPrefix("Codex Quota") == true)
            setLanguage("zh-Hans")
            precondition(panel.item.button?.toolTip?.hasPrefix("Codex 额度") == true)
            setLanguage("system")
            DispatchQueue.main.asyncAfter(deadline: .now()+0.5) { self.panel.item.button?.performClick(nil) }
            for (style, expected) in [(Style.track, 3), (.ring, 3)] {
                set("indicatorStyle", style.rawValue)
                precondition(prefs.parts == expected)
                toggle(1)
                if style == .track { precondition(prefs.parts == 2); toggle(2); precondition(prefs.parts == 2) }
                else { precondition(prefs.parts == 3); toggle(2); precondition(prefs.parts == 1) }
            }
            set("indicatorStyle", "track")
            precondition(prefs.parts == 2 && panel.item.button?.image != nil)
            toggle(1); toggle(2); precondition(prefs.parts == 1)
            DispatchQueue.main.asyncAfter(deadline: .now()+1.3) {
                self.panel.verifyVisibleContent()
                NSApp.terminate(nil)
            }
        }
    }
    func applicationWillTerminate(_ notification: Notification) {
        timer?.invalidate()
        if demo { prefs.defaults.removePersistentDomain(forName: demoSuite) }
    }
    func set(_ key: String, _ value: String) { prefs.defaults.set(value, forKey: key); update() }
    func toggle(_ bit: Int) { prefs.toggle(bit); update() }
    func refresh() {
        guard !busy && !demo else { return }
        busy = true
        DispatchQueue.global(qos: .utility).async {
            let result = Result { try RPC.fetch(cli) }
            DispatchQueue.main.async {
                self.busy = false
                switch result {
                case .success(let quota): self.quota = quota; self.error = ""
                case .failure(let error): self.quota = nil; self.error = error.localizedDescription
                }
                self.next = Date().addingTimeInterval(60)
                self.update()
            }
        }
        update()
    }
    func tick() { if Date() >= next { refresh() }; update() }
    func update() {
        objectWillChange.send()
        guard let button = panel.item.button else { return }
        let ring = prefs.style == .ring
        let fraction = window(quotaKey)?.fraction
        let key = ImageKey(ring: ring, digits: digits, marker: marker, time: !ring && prefs.parts & 2 != 0 ? time : "", parts: prefs.parts, fraction: fraction)
        if key != lastIcon {
            button.image = ring ? ringImage(number: digits, fraction: fraction, marker: marker) :
                trackImage(number: digits, marker: marker, time: time, parts: prefs.parts, fraction: fraction)
            lastIcon = key
        }
        let suffix = (ring && prefs.parts == 3 ? " · "+time : "") + (error.isEmpty && !stale ? "" : " !") + (demo ? tr(" 演示") : "")
        button.title = suffix
        button.font = timeFont
        button.imagePosition = suffix.isEmpty ? .imageOnly : .imageLeading
        button.toolTip = tr("Codex 额度 · ")+title(quotaKey)+" "+digits+" · "+title(timeKey)+tr("重置 ")+time
        button.setAccessibilityLabel(button.toolTip)
    }
    func setLanguage(_ choice: String) {
        AppLanguage.choice = choice
        lastIcon = nil
        update()
    }
    func startup(_ enabled: Bool) {
        do { try login.setEnabled(enabled) } catch { NSAlert(error: error).runModal() }
        update()
    }
}

struct QuotaView: View {
    @ObservedObject var model: QuotaApp
    func selector(_ label: String, _ key: String, _ choices: [(String,String)], _ selected: String) -> some View {
        HStack {
            Text(label).fontWeight(.semibold)
            Spacer()
            HStack(spacing: 4) {
                ForEach(choices, id: \.0) { choice in
                    chip(choice.1, name: label+" "+choice.1, selected: choice.0 == selected) {
                        model.set(key, choice.0)
                    }
                }
            }.accessibilityElement(children: .contain)
        }
    }

    private func chip(_ value: String, name: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(value).font(.system(size: 12, weight: .semibold)).monospacedDigit()
                .lineLimit(1).minimumScaleFactor(0.8)
                .frame(width: 84, height: 25)
                .foregroundColor(selected ? .white : .primary)
                .background(RoundedRectangle(cornerRadius: 6).fill(selected ? Color.accentColor : Color.secondary.opacity(0.16)))
                .contentShape(Rectangle())
        }.buttonStyle(.plain).accessibilityLabel(name).accessibilityAddTraits(selected ? .isSelected : [])
    }

    func preview(_ bit: Int, _ value: String, _ name: String) -> some View {
        chip(value, name: name, selected: model.prefs.parts & bit != 0) { model.toggle(bit) }
        .help(model.prefs.style == .ring && bit == 1 ? tr("圆环始终显示额度") : tr("点击切换，至少保留一项"))
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            PanelHeading(name: demo ? tr("Codex 额度 · 演示") : tr("Codex 额度"), symbol: "gauge.medium", color: .teal)
            Divider()
            ForEach(windows.filter { $0 == "weekly" || model.quota?.five_hour != nil }, id: \.self) { key in
                let w = model.window(key)
                VStack(alignment: .leading, spacing: 7) {
                    HStack(spacing: 12) {
                        PanelGlyph(symbol: key == "weekly" ? "calendar" : "clock", color: key == "weekly" ? .indigo : .blue)
                        Text(title(key)+tr("额度剩余")).bold()
                        Spacer()
                        Text(w.map { $0.expired ? tr("待刷新") : $0.digits+"%" } ?? "--").bold().monospacedDigit()
                    }
                    if let f = w?.fraction { ProgressView(value: f).padding(.leading, 34) }
                    Text(w?.resets_at.map { tr("重置于 ")+Date(timeIntervalSince1970: $0).formatted(Date.FormatStyle(date: .abbreviated, time: .standard).locale(AppLanguage.locale)) } ?? tr("暂无重置时间"))
                        .font(.caption).foregroundStyle(.secondary).padding(.leading, 34)
                }
                Divider()
            }
            HStack(spacing: 12) { PanelGlyph(symbol: "hourglass", color: .orange); Text(title(model.timeKey)+tr("重置倒计时")); Spacer(); Text(model.time).bold().monospacedDigit() }
            Divider()
            selector(tr("图标额度"), "quotaWindow", windows.map { ($0,title($0)) }, model.quotaKey)
            selector(tr("右侧倒计时"), "countdownWindow", windows.map { ($0,title($0)) }, model.timeKey)
            selector(tr("菜单栏样式"), "indicatorStyle", [("ring",tr("圆环")),("track",tr("跑道"))], model.prefs.style.rawValue)
            HStack { Text(tr("显示内容")).fontWeight(.semibold); Spacer(); HStack(spacing: 4) { preview(1,model.marker+" "+model.digits,tr("显示额度数值")); preview(2,model.time,tr("显示倒计时")) } }
            Text(demo ? tr("演示数据") : model.busy ? tr("正在刷新额度…") : !model.error.isEmpty ? tr(model.error) :
                    model.quota.map { tr("更新于 ")+Date(timeIntervalSince1970: $0.fetched_at).formatted(Date.FormatStyle(date: .omitted, time: .standard).locale(AppLanguage.locale))+tr(" · 每 60 秒刷新") } ?? tr("等待读取"))
                .font(.caption).foregroundStyle(.secondary)
            Divider()
            HStack { Button(tr("刷新"), action: model.refresh).disabled(demo || model.busy); Spacer()
                Button(tr("用量页面")) { NSWorkspace.shared.open(URL(string: "https://chatgpt.com/codex/settings/usage")!) }
                Spacer(); Button(tr("退出")) { NSApp.terminate(nil) } }
            Picker(AppLanguage.english ? "Language" : "语言", selection: Binding(
                get: { AppLanguage.choice }, set: model.setLanguage)) {
                ForEach(Array(zip(AppLanguage.choices, AppLanguage.names)), id: \.0) { Text($0.1).tag($0.0) }
            }
            Toggle(tr("登录系统时启动"), isOn: Binding(get: { model.login.enabled }, set: model.startup)).disabled(demo)
        }.padding(18).frame(width: AppLanguage.english ? 400 : 360).fixedSize(horizontal: false, vertical: true)
    }
}

signal(SIGPIPE, SIG_IGN)
if args.contains("--version") { print(Bundle.main.infoDictionary?["CFBundleShortVersionString"] ?? ""); exit(0) }
if args.contains("--smoke-test") && !demo { exit(2) }
if args.contains("--once") {
    do {
        let q = try demo ? Quota.example() : RPC.fetch(cli)
        if args.contains("--json") { print(String(decoding: try JSONEncoder().encode(q), as: UTF8.self)) }
        else {
            let countdown = (q.five_hour ?? q.weekly)?.countdown(weekly: q.five_hour == nil) ?? "--:--"
            func percent(_ window: Window?) -> String {
                window.map { $0.expired ? "待刷新" : $0.digits+"%" } ?? "--"
            }
            let fields = ["五小时 "+percent(q.five_hour), "每周 "+percent(q.weekly), countdown]
            print((demo ? "[演示] " : "") + fields.joined(separator: " · "))
            for (key, window) in [("五小时", q.five_hour), ("每周", q.weekly)] {
                if let end = window?.resets_at { print(key+"重置于 "+Date(timeIntervalSince1970: end).formatted(date: .abbreviated, time: .standard)) }
            }
        }
    } catch { FileHandle.standardError.write(Data((error.localizedDescription+"\n").utf8)); exit(1) }
} else {
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)
    let delegate = QuotaApp()
    app.delegate = delegate
    withExtendedLifetime(delegate) { app.run() }
}
