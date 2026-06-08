#!/usr/bin/env bash
# Render every B*.html in this dir to a same-named PNG at 1920x1080.
# Usage: bash build.sh            # render all
#        bash build.sh B08        # render only B08.html
set -u
cd "$(dirname "$0")"
shopt -s nullglob
CHROME="$(command -v chromium-browser || command -v chromium || command -v google-chrome)"
pat="${1:-}"
for f in B*.html; do
  base="${f%.html}"
  if [ -n "$pat" ] && [ "$base" != "$pat" ]; then continue; fi
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1920,1080 \
    --default-background-color=00000000 \
    --screenshot="$base.png" "$f" >/dev/null 2>&1
  if [ -f "$base.png" ]; then echo "OK  $base.png  ($(stat -c%s "$base.png") bytes)"; else echo "FAIL $base"; fi
done
