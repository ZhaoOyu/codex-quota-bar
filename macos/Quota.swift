import Foundation

struct QuotaError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

struct Window: Codable {
    let remaining: Double
    let resets_at: Double?
    var expired: Bool { resets_at.map { $0 <= Date().timeIntervalSince1970 } ?? false }
    var digits: String { expired ? "--" : String(Int(remaining)) }
    var fraction: Double? { expired ? nil : remaining / 100 }
    func countdown(weekly: Bool) -> String {
        guard let end = resets_at else { return "--:--" }
        let seconds = end - Date().timeIntervalSince1970
        guard seconds > 0 else { return "待刷新" }
        if weekly && seconds > 86400 {
            let hours = Int(seconds / 3600)
            return "\(hours / 24)天\(hours % 24)小时"
        }
        let minutes = Int(ceil(seconds / 60))
        return String(format: "%02d:%02d", minutes/60, minutes%60)
    }
}

struct Quota: Codable {
    var five_hour: Window?
    var weekly: Window?
    var fetched_at = Date().timeIntervalSince1970
    var plan = ""
    var demo = false
    static func example() -> Quota {
        let now = Date().timeIntervalSince1970
        return Quota(five_hour: Window(remaining: 78, resets_at: now+9240),
                     weekly: Window(remaining: 62, resets_at: now+300000), demo: true)
    }
    static func parse(_ response: [String: Any]) throws -> Quota {
        let buckets = response["rateLimitsByLimitId"] as? [String: Any]
        guard let bucket = (buckets?["codex"] ?? response["rateLimits"]) as? [String: Any],
              (bucket["limitId"] as? String ?? "codex") == "codex" else {
            throw QuotaError("未返回 Codex 额度，请检查 ChatGPT 登录状态。")
        }
        func number(_ value: Any?) -> Double? {
            guard let n = value as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), n.doubleValue.isFinite else { return nil }
            return n.doubleValue
        }
        var quota = Quota(plan: bucket["planType"] as? String ?? "")
        for key in ["primary", "secondary"] {
            guard let row = bucket[key] as? [String: Any], let duration = number(row["windowDurationMins"]),
                  let used = number(row["usedPercent"]) else { continue }
            let reset = number(row["resetsAt"]).flatMap { (0...253402300799).contains($0) && $0 > 0 ? $0 : nil }
            let window = Window(remaining: max(0, min(100, 100-used)), resets_at: reset)
            if duration == 300 { quota.five_hour = window }
            if duration == 10080 { quota.weekly = window }
        }
        guard quota.five_hour != nil || quota.weekly != nil else { throw QuotaError("账号未返回五小时或周额度。") }
        return quota
    }
}

// Read only the matching JSON-RPC reply. Bound the wait even when the server sends a partial line.
final class RPC {
    let process = Process(), input = Pipe(), output = Pipe()
    var buffer = Data()
    init(override: String?) throws {
        let fm = FileManager.default, home = fm.homeDirectoryForCurrentUser
        var env = ProcessInfo.processInfo.environment
        var paths = (env["PATH"] ?? "/usr/bin:/bin").components(separatedBy: ":")
        paths += ["/opt/homebrew/bin", "/usr/local/bin"] + [".npm-global/bin", ".local/bin", ".volta/bin"].map { home.appendingPathComponent($0).path }
        let nvm = URL(fileURLWithPath: env["NVM_DIR"] ?? home.appendingPathComponent(".nvm").path).appendingPathComponent("versions/node")
        let versions = (try? fm.contentsOfDirectory(atPath: nvm.path)) ?? []
        paths += versions.sorted { $0.compare($1, options: .numeric) == .orderedDescending }.map { nvm.appendingPathComponent($0+"/bin").path }
        let name = override ?? env["CODEX_QUOTA_CODEX_BIN"] ?? "codex"
        let candidates = name.contains("/") ? [(name as NSString).expandingTildeInPath] : paths.map { $0+"/"+name } +
            (name == "codex" ? ["/Applications/Codex.app/Contents/Resources/codex"] : [])
        guard let executable = candidates.first(where: fm.isExecutableFile(atPath:)) else { throw QuotaError("未找到 Codex CLI，请安装并运行 codex login。") }
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = ["app-server"]
        env["PATH"] = ([process.executableURL!.deletingLastPathComponent().path]+paths).joined(separator: ":")
        process.environment = env
        process.currentDirectoryURL = home
        process.standardInput = input
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
    }
    func close() {
        try? input.fileHandleForWriting.close()
        if process.isRunning { process.terminate() }
        for _ in 0..<20 where process.isRunning { Thread.sleep(forTimeInterval: 0.025) }
        if process.isRunning { kill(process.processIdentifier, SIGKILL) }
        process.waitUntilExit()
    }
    func send(_ message: [String: Any]) throws {
        try input.fileHandleForWriting.write(contentsOf: JSONSerialization.data(withJSONObject: message) + Data([10]))
    }
    func request(_ id: Int, _ method: String, _ params: Any = NSNull()) throws -> [String: Any] {
        try send(["id": id, "method": method, "params": params])
        let deadline = ProcessInfo.processInfo.systemUptime + 20
        let fd = output.fileHandleForReading.fileDescriptor
        while ProcessInfo.processInfo.systemUptime < deadline {
            if let end = buffer.firstIndex(of: 10) {
                let line = Data(buffer[..<end])
                buffer.removeSubrange(...end)
                guard let msg = (try? JSONSerialization.jsonObject(with: line)) as? [String: Any] else { continue }
                if msg["method"] != nil {
                    if let incoming = msg["id"] { try send(["id": incoming, "error": ["code": -32601, "message": "Unsupported"]]) }
                    continue
                }
                guard msg["id"] as? Int == id else { continue }
                guard let result = msg["result"] as? [String: Any] else { throw QuotaError("额度读取失败，请检查 Codex 登录状态。") }
                return result
            }
            var pollFD = pollfd(fd: fd, events: Int16(POLLIN), revents: 0)
            if poll(&pollFD, 1, 200) <= 0 { continue }
            var bytes = [UInt8](repeating: 0, count: 8192)
            let n = read(fd, &bytes, bytes.count)
            guard n > 0 else { throw QuotaError("Codex 连接已断开，请检查 CLI 和登录状态。") }
            buffer.append(contentsOf: bytes.prefix(n))
            guard buffer.count <= 4_000_000 else { throw QuotaError("Codex 回复超出大小限制。") }
        }
        throw QuotaError("读取超时，请稍后刷新。")
    }
    static func fetch(_ path: String?) throws -> Quota {
        let session = try RPC(override: path)
        defer { session.close() }
        _ = try session.request(1, "initialize", ["clientInfo": ["name": "codex_quota_bar", "title": "Codex Quota Bar", "version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.6"]])
        try session.send(["method": "initialized"])
        return try Quota.parse(session.request(2, "account/rateLimits/read"))
    }
}
