#!/usr/bin/env bash
# MarkItDown Desktop - GPL-3.0-or-later
# Builds "MarkItDown Desktop.app" and a distributable .dmg into ./dist
set -euo pipefail
cd "$(dirname "$0")/.."

APP="MarkItDown Desktop"
VERSION="1.0.0"
ARCH="$(uname -m)"
DMG="dist/MarkItDown-Desktop-${VERSION}-macOS-${ARCH}.dmg"

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null; then
    uv venv --python 3.12 .venv
  else
    python3 -m venv .venv   # needs Python >= 3.10
  fi
fi
if command -v uv >/dev/null; then
  uv pip install --python .venv/bin/python -r requirements-build.txt
else
  .venv/bin/python -m pip install -r requirements-build.txt
fi

[ -f assets/AppIcon.icns ] || .venv/bin/python scripts/make_icon.py

rm -rf build "dist/${APP}" "dist/${APP}.app" "$DMG"
.venv/bin/pyinstaller --noconfirm --clean --distpath dist --workpath build packaging/MarkItDownDesktop.spec

# Sign and package from a clean temp copy: iCloud-synced folders (e.g. ~/Documents)
# attach Finder xattrs that codesign rejects.
STAGE="$(mktemp -d)"
ditto --norsrc --noextattr --noacl "dist/${APP}.app" "$STAGE/${APP}.app"
xattr -cr "$STAGE/${APP}.app"
# Ad-hoc signature so the bundle is internally consistent (not notarized).
codesign --force --deep --sign - "$STAGE/${APP}.app"
codesign --verify --deep --strict "$STAGE/${APP}.app"
ln -s /Applications "$STAGE/Applications"
cp LICENSE "$STAGE/LICENSE.txt"
hdiutil create -volname "$APP" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "dist/${APP}.app"
ditto "$STAGE/${APP}.app" "dist/${APP}.app"
rm -rf "$STAGE" "dist/${APP}"

echo "Built: dist/${APP}.app"
echo "Built: $DMG"
