"""Short-lived JSON-RPC stdio client. Never reads or logs auth.json."""

import atexit
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

from . import __version__
from .model import parse_quota


class UsageError(Exception):
    pass


def cli_directories():
    """GUI launches do not inherit the shell's Homebrew/Node search paths."""
    paths = [Path(p).expanduser() for p in (
        "/opt/homebrew/bin", "/usr/local/bin", "~/.npm-global/bin",
        "~/.local/bin", "~/.volta/bin")]
    nvm = Path(os.environ.get("NVM_DIR", str(Path.home() / ".nvm")))
    # Prefer the newest installed version only when the active PATH has no CLI.
    def version(path):
        parts = path.parent.name.lstrip("v").split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts)
    paths.extend(sorted(nvm.glob("versions/node/*/bin"), key=version, reverse=True))
    return paths


def child_environment(executable):
    env = os.environ.copy()
    paths = [str(Path(executable).absolute().parent)]
    paths.extend(env.get("PATH", os.defpath).split(os.pathsep))
    paths.extend(str(p) for p in cli_directories())
    env["PATH"] = os.pathsep.join(dict.fromkeys(p for p in paths if p))
    return env


def find_codex(explicit=None):
    override = explicit or os.environ.get("CODEX_QUOTA_CODEX_BIN")
    if override:
        candidate = shutil.which(override) or str(Path(override).expanduser())
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
        raise UsageError("Codex 路径无效；请检查 --codex 或 CODEX_QUOTA_CODEX_BIN。")
    found = shutil.which("codex")
    if found:
        return found
    # Finder does not inherit the terminal's PATH. Cover common CLI installs.
    candidates = [directory / "codex" for directory in cli_directories()]
    candidates.append(Path("/Applications/Codex.app/Contents/Resources/codex"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise UsageError("未找到 Codex CLI；请安装并运行 codex login。")


class Rpc:
    def __init__(self, command, timeout=20):
        self.command = command
        self.timeout = timeout
        self.process = None
        self.messages = queue.Queue()
        self.reader = None
        self.error_reader = None
        self.failure_hint = ""
        self.sequence = 0

    def __enter__(self):
        env = child_environment(self.command[0])
        try:
            self.process = subprocess.Popen(
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env,
                cwd=str(Path.home()), bufsize=1)
        except OSError:
            raise UsageError("无法启动 Codex CLI；请检查安装和执行权限。") from None
        self.error_reader = threading.Thread(target=self._read_errors, daemon=True)
        self.error_reader.start()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        atexit.register(self.close)
        return self

    def _read_errors(self):
        # Drain continuously to avoid pipe deadlocks. Store only fixed hints,
        # never server text, which can contain account data or credentials.
        for line in iter(lambda: self.process.stderr.readline(4096), ""):
            lower = line.lower()
            if "node" in lower and ("no such file" in lower or "not found" in lower):
                self.failure_hint = "找不到 Node.js；请安装 Node 或从已加载 Node 的终端启动。"
            elif "unexpected argument" in lower or "unrecognized subcommand" in lower:
                self.failure_hint = "Codex CLI 不支持所需命令；请升级 Codex CLI。"
            elif "bad cpu type" in lower or "exec format error" in lower:
                self.failure_hint = "Codex 或 Node 的架构不兼容；请安装适配这台 Mac 的版本。"
            elif "read-only file system" in lower or "permission denied" in lower:
                self.failure_hint = "Codex 启动遇到目录或执行权限问题；请在终端检查 codex app-server。"

    def disconnected(self):
        # Wait briefly for stderr classification after a short-lived process exits.
        if self.error_reader:
            self.error_reader.join(timeout=0.2)
        if self.failure_hint:
            return UsageError(self.failure_hint)
        code = self.process.poll()
        suffix = f"（退出码 {code}）" if code is not None else ""
        return UsageError(f"Codex 提前退出或连接断开{suffix}；请在终端运行 codex app-server 检查启动错误。")

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                    if isinstance(message, dict):
                        self.messages.put(message)
                except (ValueError, UnicodeError):
                    continue
        finally:
            self.messages.put(None)

    def send(self, message):
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise self.disconnected() from None

    def request(self, method, params=None):
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise UsageError("读取超时；请检查网络，稍后自动重试。")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty:
                raise UsageError("读取超时；请检查网络，稍后自动重试。") from None
            if message is None:
                raise self.disconnected()
            if "method" in message:
                if "id" in message:
                    # This client never approves tools, shell commands or token refresh requests.
                    self.send({"id": message["id"], "error": {
                        "code": -32601, "message": "Unsupported by read-only quota client"}})
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                # Do not expose server messages: they may contain credentials or private paths.
                raise UsageError("额度读取失败；请运行 codex login，以 ChatGPT 账号登录后重试。")
            if not isinstance(message.get("result"), dict):
                raise UsageError("Codex 返回格式异常；请升级 CLI 后重试。")
            return message["result"]

    def __exit__(self, *_):
        self.close()
        atexit.unregister(self.close)

    def close(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
            if self.reader:
                self.reader.join(timeout=2)
            if self.error_reader:
                self.error_reader.join(timeout=2)
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()


def fetch_quota(codex=None):
    # stdio is the default, including older CLI versions without --listen.
    with Rpc([find_codex(codex), "app-server"]) as rpc:
        rpc.request("initialize", {"clientInfo": {
            "name": "codex_quota_bar", "title": "Codex Quota Bar", "version": __version__}})
        rpc.send({"method": "initialized"})
        result = rpc.request("account/rateLimits/read")
    try:
        return parse_quota(result, time.time())
    except ValueError as error:
        raise UsageError(str(error)) from None

