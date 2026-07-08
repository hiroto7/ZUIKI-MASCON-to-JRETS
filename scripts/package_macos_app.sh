#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ZUIKI-MASCON-to-JRETS"

uv run python scripts/build_app_icon.py
uv run pyinstaller --noconfirm --name "$APP_NAME" --noconsole --icon build/app-icon.icns main.py

cd dist
codesign --verify --deep --strict "$APP_NAME.app"
ditto -c -k --sequesterRsrc --keepParent "$APP_NAME.app" "$APP_NAME.app.zip"
