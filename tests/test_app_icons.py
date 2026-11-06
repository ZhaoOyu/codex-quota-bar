"""Validate packaged application artwork without optional image dependencies."""
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "packaging/icons"


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError("Not a PNG")
    return struct.unpack(">II", data[16:24])


class AppIconTests(unittest.TestCase):
    def test_png_sizes_and_alpha(self):
        for size in (16, 24, 32, 48, 64, 128, 256, 512, 1024):
            with self.subTest(size=size):
                data = (ICONS / f"codex-quota-bar-{size}.png").read_bytes()
                self.assertEqual(png_size(data), (size, size))
                self.assertEqual(data[25], 6, "RGBA transparency must be preserved")

    def test_icns_contains_retina_artwork(self):
        data = (ICONS / "AppIcon.icns").read_bytes()
        self.assertEqual(data[:4], b"icns")
        self.assertEqual(struct.unpack(">I", data[4:8])[0], len(data))
        offset, sizes = 8, set()
        while offset < len(data):
            length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
            self.assertGreaterEqual(length, 8)
            self.assertLessEqual(offset + length, len(data))
            payload = data[offset + 8:offset + length]
            if payload.startswith(b"\x89PNG"):
                sizes.add(png_size(payload))
            offset += length
        self.assertEqual(offset, len(data))
        self.assertTrue({(128, 128), (256, 256), (512, 512), (1024, 1024)} <= sizes)

    def test_desktop_launcher_uses_app_icon(self):
        desktop = (ROOT / "packaging/codex-quota-bar.desktop").read_text()
        self.assertIn("\nIcon=codex-quota-bar\n", desktop)
