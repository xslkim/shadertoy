#!/bin/bash
# 批量把 ep2/_diagrams/*.html 渲染成 ep2/assets/*.png
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
DIR="D:/shadertoy/ocean/video/ep2/_diagrams"
OUT="D:\\shadertoy\\ocean\\video\\ep2\\assets"
cd "$DIR"
for f in "$@"; do
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --screenshot="$OUT\\$f.png" \
    --window-size=1920,1080 --default-background-color=ff0d1117 \
    "file:///D:/shadertoy/ocean/video/ep2/_diagrams/$f.html" 2>&1 | grep -o "written to file.*" || echo "FAIL: $f"
done
