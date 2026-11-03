import Foundation

/// A per-user login item launches the normal app quietly, with no elevated helper.
struct LoginItem {
    let identifier: String
    var arguments = ["--background"]
    var directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/LaunchAgents")
    var url: URL { directory.appendingPathComponent(identifier + ".plist") }
    var enabled: Bool { FileManager.default.fileExists(atPath: url.path) }

    func setEnabled(_ enabled: Bool) throws {
        if !enabled {
            if self.enabled { try FileManager.default.removeItem(at: url) }
            return
        }
        guard let executable = Bundle.main.executableURL else { throw CocoaError(.fileNoSuchFile) }
        let item: [String: Any] = ["Label": identifier, "RunAtLoad": true,
                                   "ProgramArguments": [executable.path] + arguments]
        let data = try PropertyListSerialization.data(fromPropertyList: item, format: .xml, options: 0)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try data.write(to: url, options: .atomic)
    }
}
