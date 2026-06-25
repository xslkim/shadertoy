#!/bin/bash
# 批量把 ep1/_diagrams/*.html 渲染成 ep1/assets/*.png
# 用法：./render.sh B02 B04 ...   或   ./render.sh $(ls *.html | sed 's/.html//')
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
DIR="D:/shadertoy/webrtc/ep1/_diagrams"
OUT="D:\\shadertoy\\webrtc\\ep1\\assets"
cd "$DIR"
for f in "$@"; do
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --screenshot="$OUT\\$f.png" \
    --window-size=1920,1080 --default-background-color=ff0d1117 \
    "file:///D:/shadertoy/webrtc/ep1/_diagrams/$f.html" 2>&1 | grep -o "written to file.*" || echo "FAIL: $f"
done
