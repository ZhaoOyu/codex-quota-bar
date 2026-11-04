"""Render the actual tray SVG on a dark panel background using demo readings."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_quota_bar.linux import track_icon
from gi.repository import GdkPixbuf


def main():
    scale = 3
    readings = (("W 72 · 6天16小时", .72), ("H 78 · 02:34", .78), ("W 62", .62))
    canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 480, 270)
    canvas.fill(0x141414ff)
    for index, (reading, value) in enumerate(readings):
        loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
        loader.connect("size-prepared", lambda loader, width, height: loader.set_size(width * scale, height * scale))
        loader.write(track_icon(reading, value).encode())
        loader.close()
        icon = loader.get_pixbuf()
        icon.composite(canvas, 24, index * 84 + 9, icon.get_width(), icon.get_height(),
                       24, index * 84 + 9, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
    output = ROOT / "dist/linux-track-preview.png"
    output.parent.mkdir(exist_ok=True)
    canvas.savev(str(output), "png", [], [])
    print(output)


if __name__ == "__main__":
    main()
