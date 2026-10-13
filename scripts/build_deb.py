"""Build an architecture-independent Ubuntu package without root or pip."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from codex_quota_bar import __version__


def main():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex-quota-deb-") as directory:
        stage = Path(directory)
        app = stage / "usr/lib/codex-quota-bar"
        app.mkdir(parents=True)
        shutil.copytree(ROOT / "codex_quota_bar", app / "codex_quota_bar",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "launcher.py", app / "launcher.py")
        binary = stage / "usr/bin/codex-quota-bar"
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/lib/codex-quota-bar/launcher.py "$@"\n')
        binary.chmod(0o755)
        desktop = stage / "usr/share/applications"
        desktop.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/codex-quota-bar.desktop", desktop)
        docs = stage / "usr/share/doc/codex-quota-bar"
        docs.mkdir(parents=True)
        shutil.copy2(ROOT / "LICENSE", docs / "copyright")
        shutil.copy2(ROOT / "README.md", docs)
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            f"Package: codex-quota-bar\nVersion: {__version__}\nArchitecture: all\n"
            "Maintainer: Codex Quota Bar contributors <noreply@users.noreply.github.com>\n"
            "Section: utils\nPriority: optional\n"
            "Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1\n"
            "Recommends: gnome-shell-extension-appindicator\n"
            "Description: Codex five-hour and weekly quota in the top panel\n"
            " Native status indicator using the local Codex CLI login.\n")
        # TemporaryDirectory is 0700; never ship that as the filesystem root.
        stage.chmod(0o755)
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path == binary else 0o644)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage),
                        str(output / f"codex-quota-bar_{__version__}_all.deb")], check=True)


if __name__ == "__main__":
    main()

