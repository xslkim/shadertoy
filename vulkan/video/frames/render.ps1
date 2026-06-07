# 把 video/frames/ 下的 v*.html 全部光栅化为 1920×1080 PNG(用无头 Edge)。
# 用法:在本目录运行  powershell -ExecutionPolicy Bypass -File render.ps1
$edge = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Error "未找到 msedge.exe"; exit 1 }

$dir = $PSScriptRoot
Get-ChildItem "$dir\v*.html" | ForEach-Object {
  $n = $_.BaseName
  $out = "$dir\$n.png"
  $udd = "$env:TEMP\edgeshot_$n"
  if (Test-Path $out) { Remove-Item $out -Force }
  & $edge --headless=new --disable-gpu --no-first-run --user-data-dir="$udd" `
    --hide-scrollbars --allow-file-access-from-files --force-device-scale-factor=1 `
    --window-size=1920,1080 --virtual-time-budget=3000 `
    --screenshot="$out" ("file:///" + $_.FullName.Replace('\','/')) 2>$null | Out-Null
  Remove-Item $udd -Recurse -Force -ErrorAction SilentlyContinue
  Write-Output ("{0,-18} {1}" -f $n, $(if(Test-Path $out){"OK"}else{"FAILED"}))
}
