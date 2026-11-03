$ErrorActionPreference = "Stop"
# 在桌面创建「跑团 KP」快捷方式，指向本目录下的 启动.vbs。
# 用法：右键「使用 PowerShell 运行」，或在终端里 .\make_shortcut.ps1
$appDir = $PSScriptRoot
$vbs = Join-Path $appDir "启动.vbs"
$icon = Join-Path $appDir "kp.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "跑团 KP.lnk"

if (-not (Test-Path $vbs)) { Write-Host ("找不到 " + $vbs); exit 1 }

$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $vbs
$s.WorkingDirectory = $appDir
$s.Description = "跑团 KP - 本地 COC/DND 跑团工具"
$s.WindowStyle = 1
if (Test-Path $icon) { $s.IconLocation = $icon + ",0" }
$s.Save()

Write-Host ("快捷方式: " + $lnk)
Write-Host ("指向: " + $vbs)
Write-Host ("图标: " + $icon)
