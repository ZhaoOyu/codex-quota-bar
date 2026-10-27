# Build on macOS: python -m PyInstaller --noconfirm packaging/macos.spec
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis([str(root / 'launcher.py')], pathex=[str(root)],
             binaries=[], datas=[], hiddenimports=['rumps', 'AppKit', 'Foundation'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['gi', 'tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Codex Quota Bar',
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Codex Quota Bar')
app = BUNDLE(coll, name='Codex Quota Bar.app', bundle_identifier='io.github.codex-quota-bar',
             info_plist={'LSUIElement': True, 'CFBundleShortVersionString': '0.1.3',
                         'NSHighResolutionCapable': True})

