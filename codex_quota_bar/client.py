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
    for path in ("/opt/homebrew/bin/codex", "/usr/local/bin/codex",
                 "~/.npm-global/bin/codex", "~/.local/bin/codex",
                 "/Applications/Codex.app/Contents/Resources/codex"):
        candidate = Path(path).expanduser()
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
        self.sequence = 0

    def __enter__(self):
        env = os.environ.copy()
        # A globally installed npm launcher may need node in the same directory.
        env["PATH"] = str(Path(self.command[0]).parent) + os.pathsep + env.get("PATH", "")
        try:
            self.process = subprocess.Popen(
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=env,
                cwd=str(Path.home()), bufsize=1)
        except OSError:
            raise UsageError("无法启动 Codex CLI；请检查安装和执行权限。") from None
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        atexit.register(self.close)
        return self

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
            raise UsageError("Codex 连接已断开；请重试。") from None

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
                raise UsageError("Codex 提前退出；请检查 CLI 版本与登录状态。")
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
            self.process.stdin.close()
            self.process.stdout.close()


def fetch_quota(codex=None):
    with Rpc([find_codex(codex), "app-server", "--listen", "stdio://"]) as rpc:
        rpc.request("initialize", {"clientInfo": {
            "name": "codex_quota_bar", "title": "Codex Quota Bar", "version": __version__}})
        rpc.send({"method": "initialized"})
        result = rpc.request("account/rateLimits/read")
    try:
        return parse_quota(result, time.time())
    except ValueError as error:
        raise UsageError(str(error)) from None

