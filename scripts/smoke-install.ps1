param(
  [string]$SourceDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

function Assert-Exists([string]$Path) {
  if (-not (Test-Path $Path)) {
    throw "Expected path was not created: $Path"
  }
}

function Assert-Missing([string]$Path) {
  if (Test-Path $Path) {
    throw "Expected path was not removed: $Path"
  }
}

function Assert-GuiShortcut([string]$Path, [bool]$SafeDisplay) {
  Assert-Exists $Path
  $shortcut = $script:ShortcutShell.CreateShortcut($Path)
  if ($shortcut.TargetPath -notlike "*wscript.exe") {
    throw "Expected GUI shortcut to target wscript.exe: $Path"
  }
  if ($shortcut.Arguments -notlike "*launch-gui.vbs*") {
    throw "Expected GUI shortcut to use launch-gui.vbs: $Path"
  }
  $hasSafeDisplay = $shortcut.Arguments -like "*--safe-display*"
  if ($SafeDisplay -and -not $hasSafeDisplay) {
    throw "Expected safe display shortcut argument: $Path"
  }
  if (-not $SafeDisplay -and $hasSafeDisplay) {
    throw "Normal GUI shortcut must not include --safe-display: $Path"
  }
}

function Assert-UninstallShortcut([string]$Path) {
  Assert-Exists $Path
  $shortcut = $script:ShortcutShell.CreateShortcut($Path)
  if ($shortcut.TargetPath -notlike "*uninstall-auto-note.bat") {
    throw "Expected uninstall shortcut target: $Path"
  }
}

$source = [System.IO.Path]::GetFullPath($SourceDir)
$install = Join-Path ([System.IO.Path]::GetTempPath()) ("auto-note-smoke-" + [guid]::NewGuid().ToString("N"))
$shortcutRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("auto-note-shortcuts-smoke-" + [guid]::NewGuid().ToString("N"))
$desktopShortcuts = Join-Path $shortcutRoot "Desktop"
$startShortcuts = Join-Path $shortcutRoot "StartMenu"
$script:ShortcutShell = New-Object -ComObject WScript.Shell

& (Join-Path $source "scripts\install-auto-note.ps1") `
  -SourceDir $source `
  -InstallDir $install `
  -DesktopShortcutDir $desktopShortcuts `
  -StartMenuShortcutDir $startShortcuts `
  -SkipEnv

Assert-Exists (Join-Path $install "auto-note-gui.bat")
Assert-Exists (Join-Path $install "scripts\install-auto-note.ps1")
Assert-Exists (Join-Path $install "scripts\uninstall-auto-note.ps1")
Assert-Exists (Join-Path $install "shortcuts\uninstall-auto-note.bat")
Assert-Exists (Join-Path $install "docs\INSTALL.md")
Assert-Exists (Join-Path $install "docs\COMMERCIAL_POLICY_DRAFT.md")
Assert-Exists (Join-Path $install "articles")
Assert-Exists (Join-Path $install ".auto-note")
Assert-Exists (Join-Path $install ".auto-note\install-info.json")
Assert-GuiShortcut (Join-Path $desktopShortcuts "auto-note.lnk") $false
Assert-GuiShortcut (Join-Path $desktopShortcuts "auto-note safe display.lnk") $true
Assert-GuiShortcut (Join-Path $startShortcuts "auto-note.lnk") $false
Assert-GuiShortcut (Join-Path $startShortcuts "auto-note safe display.lnk") $true
Assert-UninstallShortcut (Join-Path $startShortcuts "auto-note uninstall.lnk")

$article = Join-Path $install "articles\keep.md"
"keep" | Set-Content -LiteralPath $article -Encoding UTF8

& (Join-Path $source "scripts\install-auto-note.ps1") `
  -SourceDir $source `
  -InstallDir $install `
  -DesktopShortcutDir $desktopShortcuts `
  -StartMenuShortcutDir $startShortcuts `
  -SkipEnv

$backupDir = Join-Path $install ".auto-note\install-backups"
Assert-Exists $backupDir
$backups = @(Get-ChildItem -LiteralPath $backupDir -Filter "*.zip")
if ($backups.Count -lt 1) {
  throw "Expected a pre-install backup zip in: $backupDir"
}
$installInfo = Get-Content -LiteralPath (Join-Path $install ".auto-note\install-info.json") -Raw | ConvertFrom-Json
if (-not $installInfo.preinstall_backup) {
  throw "Expected install-info.json to record preinstall_backup."
}

& (Join-Path $source "scripts\install-auto-note.ps1") `
  -SourceDir $source `
  -InstallDir $install `
  -DesktopShortcutDir $desktopShortcuts `
  -StartMenuShortcutDir $startShortcuts `
  -SkipEnv

$backups = @(Get-ChildItem -LiteralPath $backupDir -Filter "*.zip")
if ($backups.Count -lt 2) {
  throw "Expected repeated updates to keep multiple pre-install backups in: $backupDir"
}
$backupNames = @($backups | ForEach-Object { $_.Name } | Sort-Object -Unique)
if ($backupNames.Count -ne $backups.Count) {
  throw "Expected pre-install backup names to be unique."
}

& (Join-Path $source "scripts\uninstall-auto-note.ps1") `
  -InstallDir $install `
  -DesktopShortcutDir $desktopShortcuts `
  -StartMenuShortcutDir $startShortcuts

Assert-Missing (Join-Path $install "auto-note-gui.bat")
Assert-Missing (Join-Path $install "src")
Assert-Missing (Join-Path $desktopShortcuts "auto-note.lnk")
Assert-Missing (Join-Path $desktopShortcuts "auto-note safe display.lnk")
Assert-Missing (Join-Path $startShortcuts "auto-note.lnk")
Assert-Missing (Join-Path $startShortcuts "auto-note safe display.lnk")
Assert-Missing (Join-Path $startShortcuts "auto-note uninstall.lnk")
Assert-Exists $article
Assert-Exists (Join-Path $install ".auto-note")

& (Join-Path $source "scripts\uninstall-auto-note.ps1") `
  -InstallDir $install `
  -RemoveUserData `
  -DesktopShortcutDir $desktopShortcuts `
  -StartMenuShortcutDir $startShortcuts

Assert-Missing $install
if (Test-Path $shortcutRoot) {
  Remove-Item -LiteralPath $shortcutRoot -Recurse -Force
}

Write-Host "install/uninstall smoke OK"
