#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
app="Codex Quota Bar"
out=${1:-dist}
mkdir -p "$out" build
stage=$(mktemp -d "$PWD/build/swift.XXXXXX")
trap 'rm -rf "$stage"' EXIT
bundle="$stage/$app.app/Contents"
mkdir -p "$bundle/MacOS" "$bundle/Resources"
if [ -d /Applications/Xcode.app/Contents/Developer ]; then export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer; fi
xcrun swiftc -swift-version 5 -O -target "$(uname -m)-apple-macosx13.0" -module-cache-path "$PWD/build/swift-module-cache" macos/*.swift -o "$bundle/MacOS/$app"
version=$(python3 -c 'from codex_quota_bar import __version__; print(__version__)')
python3 - "$bundle/Info.plist" "$version" <<'PY'
import sys, plistlib
with open(sys.argv[1], 'wb') as f:
    plistlib.dump(dict(CFBundleIdentifier='io.github.codex-quota-bar',CFBundleExecutable='Codex Quota Bar',CFBundleName='Codex Quota Bar',CFBundleIconFile='AppIcon.icns',CFBundlePackageType='APPL',CFBundleShortVersionString=sys.argv[2],CFBundleVersion=sys.argv[2],LSUIElement=True,LSMinimumSystemVersion='13.0',NSHighResolutionCapable=True),f)
PY
cp packaging/icons/AppIcon.icns "$bundle/Resources/"
cp LICENSE "$bundle/Resources/"
codesign --force --sign - "$stage/$app.app"
codesign --verify --deep --strict "$stage/$app.app"
if [ -e "$out/$app.app" ]; then mv "$out/$app.app" "$stage/previous.app"; fi
mv "$stage/$app.app" "$out/"
