param(
  [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$ShortcutPath = ""
)

$ErrorActionPreference = "Stop"

$project = (Resolve-Path $ProjectDir).Path
$target = Join-Path $project "auto-note-gui.bat"
if (-not (Test-Path $target)) {
  throw "auto-note-gui.bat was not found: $target"
}
$launcher = Join-Path $project "scripts\launch-gui.vbs"
if (-not (Test-Path $launcher)) {
  throw "launch-gui.vbs was not found: $launcher"
}

if (-not $ShortcutPath) {
  $ShortcutPath = Join-Path $project "auto-note.lnk"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\wscript.exe"
$shortcut.Arguments = "`"$launcher`""
$shortcut.WorkingDirectory = $project
$shortcut.Description = "auto-note GUI"
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,101"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Created shortcut:"
Write-Host $ShortcutPath

$legacyShortcutPath = Join-Path $project "auto-note GUI.lnk"
if ($ShortcutPath -ne $legacyShortcutPath) {
  $legacy = $shell.CreateShortcut($legacyShortcutPath)
  $legacy.TargetPath = "$env:SystemRoot\System32\wscript.exe"
  $legacy.Arguments = "`"$launcher`""
  $legacy.WorkingDirectory = $project
  $legacy.Description = "auto-note GUI"
  $legacy.IconLocation = "$env:SystemRoot\System32\imageres.dll,101"
  $legacy.WindowStyle = 1
  $legacy.Save()
}
