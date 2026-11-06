"""Convert the approved RGBA artwork into app icons (requires Pillow).

Generated assets are committed so normal package builds do not require Pillow.
This only resizes/converts the artwork; live quota indicator graphics are separate.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "packaging/icons"
SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def main():
    with Image.open(ICONS / "source.png") as source:
        if source.width != source.height or source.mode != "RGBA":
            raise ValueError("Expected square RGBA source artwork")
        for size in SIZES:
            source.resize((size, size), Image.Resampling.LANCZOS).save(
                ICONS / f"codex-quota-bar-{size}.png", optimize=True)
        source.resize((1024, 1024), Image.Resampling.LANCZOS).save(
            ICONS / "AppIcon.icns", format="ICNS")
    print(f"Generated {len(SIZES)} PNG sizes and AppIcon.icns in {ICONS}")


if __name__ == "__main__":
    main()
