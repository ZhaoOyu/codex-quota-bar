# Application artwork

`source.png` is the approved blue/mint quota-ring and code-bracket artwork,
generated using the built-in image generation tool. Its transparent exterior is
preserved. It is an independent application mark, not the OpenAI logo.

Regenerate packaged sizes with `python3 scripts/build_icons.py` (Pillow required
for this developer-only step). PNGs and the ICNS are committed; ordinary package
builds do not require an image library. No creative changes are applied during
conversion.

Ubuntu installs the PNGs in the hicolor application icon theme. The macOS bundle
uses `AppIcon.icns` through `CFBundleIconFile`. Live menu-bar/tray quota rings and
tracks are separate graphics and are intentionally unchanged.
