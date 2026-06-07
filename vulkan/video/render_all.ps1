# 一键把所有视觉元素(教学帧 / 封面 / 动画序列)光栅化为 PNG。
# 用法:powershell -ExecutionPolicy Bypass -File render_all.ps1
$edge = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Error "未找到 msedge.exe"; exit 1 }
$root = $PSScriptRoot

function Shot($url, $out, $size) {
  $udd = Join-Path $env:TEMP ("es_" + [guid]::NewGuid().ToString("N"))
  & $edge --headless=new --disable-gpu --no-first-run "--user-data-dir=$udd" --hide-scrollbars `
    --allow-file-access-from-files --force-device-scale-factor=1 "--window-size=$size" `
    --virtual-time-budget=3000 "--screenshot=$out" $url 2>$null | Out-Null
  Write-Output ("{0,-26} {1}" -f (Split-Path $out -Leaf), $(if (Test-Path $out) { "OK" } else { "FAIL" }))
}
function U($p) { "file:///" + ($p -replace '\\','/') }

# 1) 教学帧 frames/v*.html -> 1920x1080
Get-ChildItem "$root\frames\v*.html" | ForEach-Object {
  Shot (U $_.FullName) "$root\frames\$($_.BaseName).png" "1920,1080"
}
# 2) 封面 thumbnails
Shot (U "$root\thumbnails\cover_youtube.html")  "$root\thumbnails\cover_youtube.png"  "1280,720"
Shot (U "$root\thumbnails\cover_bilibili.html") "$root\thumbnails\cover_bilibili.png" "1146,717"
# 3) 动画序列(逐 step)
foreach ($s in 0..3) { Shot ((U "$root\anim\anim_evolution.html") + "?step=$s") "$root\anim\evo_$s.png"   "1920,1080" }
foreach ($s in 0..7) { Shot ((U "$root\anim\anim_heap.html")      + "?step=$s") "$root\anim\heap_$s.png"  "1920,1080" }
foreach ($s in 0..4) { Shot ((U "$root\anim\anim_index.html")     + "?step=$s") "$root\anim\index_$s.png" "1920,1080" }
