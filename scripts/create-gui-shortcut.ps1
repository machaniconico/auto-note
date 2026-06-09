param(
  [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$ShortcutPath = "",
  [string]$SafeDisplayShortcutPath = ""
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

function New-AutoNoteShortcut([string]$Path, [string]$Arguments, [string]$Description) {
  $shortcut = $shell.CreateShortcut($Path)
  $shortcut.TargetPath = "$env:SystemRoot\System32\wscript.exe"
  $shortcut.Arguments = $Arguments
  $shortcut.WorkingDirectory = $project
  $shortcut.Description = $Description
  $shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,101"
  $shortcut.WindowStyle = 1
  $shortcut.Save()
}

$normalArguments = "`"$launcher`""
$safeDisplayArguments = "`"$launcher`" --safe-display"

New-AutoNoteShortcut $ShortcutPath $normalArguments "auto-note GUI"

Write-Host "Created shortcut:"
Write-Host $ShortcutPath

$legacyShortcutPath = Join-Path $project "auto-note GUI.lnk"
if ($ShortcutPath -ne $legacyShortcutPath) {
  New-AutoNoteShortcut $legacyShortcutPath $normalArguments "auto-note GUI"
}

if ($SafeDisplayShortcutPath) {
  New-AutoNoteShortcut $SafeDisplayShortcutPath $safeDisplayArguments "auto-note GUI (safe display)"
  Write-Host "Created safe display shortcut:"
  Write-Host $SafeDisplayShortcutPath
}
