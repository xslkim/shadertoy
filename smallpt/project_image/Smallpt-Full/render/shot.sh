#!/bin/bash
# usage: shot.sh B02 [B03 ...]
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
ROOT="D:/shadertoy/smallpt/project_image/Smallpt-Full"
for id in "$@"; do
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1920,1080 --default-background-color=0d1117ff \
    --screenshot="$ROOT/assets/$id.png" "file:///$ROOT/render/$id.html" 2>/dev/null
  echo "shot $id -> assets/$id.png ($(stat -c%s "$ROOT/assets/$id.png" 2>/dev/null) bytes)"
done
