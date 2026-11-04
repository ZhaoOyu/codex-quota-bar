"""Run GNOME in a private D-Bus/Wayland session, never modify the user's Shell."""
import json
import contextlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
UUID = "codex-quota-bar@zhaooyu.github.io"
TEST_UUID = "codex-quota-test@local"


def session(directory):
    directory = Path(directory)
    subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions",
                    str([UUID, TEST_UUID])], check=True)
    subprocess.run(["gsettings", "set", "org.gnome.shell", "disable-user-extensions", "false"], check=True)
    log = ROOT / "dist/gnome-smoke.log"
    with log.open("w") as output:
        shell = subprocess.Popen(["gnome-shell", "--headless", "--wayland", "--no-x11",
            "--virtual-monitor", "1280x1000", "--wayland-display", "codex-quota-test"],
            stdout=output, stderr=subprocess.STDOUT)
        backend = None
        try:
            for _ in range(200):
                if (directory / "run/codex-quota-test").exists():
                    break
                if shell.poll() is not None:
                    raise RuntimeError("Headless GNOME exited; inspect dist/gnome-smoke.log")
                time.sleep(.1)
            else:
                raise RuntimeError("Wayland socket did not appear")
            time.sleep(1)
            env = dict(os.environ, WAYLAND_DISPLAY="codex-quota-test", GDK_BACKEND="wayland")
            backend = subprocess.Popen([sys.executable, "-m", "codex_quota_bar", "--demo"],
                cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
            result = Path(os.environ["CODEX_GNOME_TEST_RESULT"])
            for _ in range(600):
                if result.exists():
                    data = json.loads(result.read_text())
                    print(json.dumps(data, ensure_ascii=False))
                    return 0 if data.get("ok") else 1
                if shell.poll() is not None or backend.poll() is not None:
                    raise RuntimeError("Test process exited; inspect dist/gnome-smoke.log")
                time.sleep(.1)
            raise RuntimeError("Timed out; inspect dist/gnome-smoke.log")
        finally:
            for process in (backend, shell):
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--session":
        return session(sys.argv[2])
    (ROOT / "dist").mkdir(exist_ok=True)
    # Session portals may leave FUSE mounts temporarily; retain this isolated
    # directory for inspection rather than recursively deleting live mounts.
    with contextlib.nullcontext(tempfile.mkdtemp(prefix="codex-gnome-smoke-")) as temporary:
        print("Isolated test data:", temporary, flush=True)
        directory = Path(temporary)
        for name in ("run", "config", "cache", "data"):
            (directory / name).mkdir(mode=0o700)
        preferences = directory / "config/codex-quota-bar"
        preferences.mkdir()
        (preferences / "preferences.json").write_text(json.dumps({"interfaceLanguage": "zh-Hans"}))
        extensions = directory / "data/gnome-shell/extensions"
        shutil.copytree(ROOT / "gnome", extensions / UUID)
        test = extensions / TEST_UUID
        test.mkdir()
        shutil.copy2(ROOT / "scripts/gnome_smoke_driver.js", test / "extension.js")
        (test / "metadata.json").write_text(json.dumps({"uuid": TEST_UUID, "name": "Test Driver",
            "description": "Isolated test only", "shell-version": ["45", "46", "47", "48", "49", "50"]}))
        env = dict(os.environ, XDG_RUNTIME_DIR=str(directory / "run"),
            XDG_CONFIG_HOME=str(directory / "config"), XDG_DATA_HOME=str(directory / "data"),
            XDG_CACHE_HOME=str(directory / "cache"), XDG_SESSION_TYPE="wayland", XDG_CURRENT_DESKTOP="GNOME",
            CODEX_GNOME_TEST_RESULT=str(directory / "result.json"),
            CODEX_GNOME_TEST_IMAGE=str(ROOT / "dist/gnome-panel-preview.png"),
            LIBGL_ALWAYS_SOFTWARE="1", GIO_USE_VFS="local", GDK_BACKEND="wayland")
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            env.pop(key, None)
        return subprocess.run(["dbus-run-session", "--", sys.executable, __file__, "--session", temporary],
                              env=env, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
