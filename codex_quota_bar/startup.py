"""Explicit, user-controlled login startup registration."""

import os
from pathlib import Path
import plistlib
import sys


def launch_command():
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        launcher = Path(__file__).resolve().parent.parent / "launcher.py"
        command = ([sys.executable, str(launcher)] if launcher.is_file()
                   else [sys.executable, "-m", "codex_quota_bar"])
    # Preserve an explicit CLI selection, but never persist --demo/--smoke-test.
    codex = os.environ.get("CODEX_QUOTA_CODEX_BIN")
    for index, argument in enumerate(sys.argv[1:], 1):
        if argument == "--codex" and index + 1 < len(sys.argv):
            codex = sys.argv[index + 1]
        elif argument.startswith("--codex="):
            codex = argument.split("=", 1)[1]
    if codex:
        from .client import find_codex
        command += ["--codex", str(Path(find_codex(codex)).absolute())]
    return command


def startup_path():
    if sys.platform == "darwin":
        return Path.home() / "Library/LaunchAgents/io.github.codex-quota-bar.plist"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart/codex-quota-bar.desktop"


def is_enabled():
    return startup_path().is_file()


def desktop_quote(arg):
    # Desktop Entry Exec has its own grammar; percent is a field-code escape.
    return '"' + arg.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def set_enabled(enabled):
    path = startup_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    command = launch_command()
    if sys.platform == "darwin":
        content = plistlib.dumps({"Label": "io.github.codex-quota-bar",
                                 "ProgramArguments": command, "RunAtLoad": True})
    else:
        content = ("[Desktop Entry]\nType=Application\nName=Codex Quota Bar\n"
                   "Exec=" + " ".join(map(desktop_quote, command)) +
                   "\nTerminal=false\nX-GNOME-Autostart-enabled=true\n").encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.chmod(0o600)
    temporary.replace(path)

