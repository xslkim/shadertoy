#!/bin/bash
# 批量把 _diagrams/*.html 渲染成 assets/*.png
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
DIR="D:/AutoVideo/project/SDF Raymarching/_diagrams"
OUT="D:\\AutoVideo\\project\\SDF Raymarching\\assets"
cd "$DIR"
for f in "$@"; do
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --screenshot="$OUT\\$f.png" \
    --window-size=1920,1080 --default-background-color=ff0d1117 \
    "file:///D:/AutoVideo/project/SDF Raymarching/_diagrams/$f.html" 2>&1 | grep -o "written to file.*" || echo "FAIL: $f"
done
