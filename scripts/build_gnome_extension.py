"""Build the optional GNOME 45+ extension without installing or enabling it."""
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parent.parent
UUID = "codex-quota-bar@zhaooyu.github.io"
FILES = ("metadata.json", "extension.js", "stylesheet.css")


def main():
    metadata = json.loads((ROOT / "gnome/metadata.json").read_text())
    assert metadata["uuid"] == UUID
    output = ROOT / "dist" / f"{UUID}.shell-extension.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / "gnome" / name, name)
    print(output)


if __name__ == "__main__":
    main()
