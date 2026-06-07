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

$source = [System.IO.Path]::GetFullPath($SourceDir)
$install = Join-Path ([System.IO.Path]::GetTempPath()) ("auto-note-smoke-" + [guid]::NewGuid().ToString("N"))

& (Join-Path $source "scripts\install-auto-note.ps1") `
  -SourceDir $source `
  -InstallDir $install `
  -NoShortcuts `
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

$article = Join-Path $install "articles\keep.md"
"keep" | Set-Content -LiteralPath $article -Encoding UTF8

& (Join-Path $source "scripts\install-auto-note.ps1") `
  -SourceDir $source `
  -InstallDir $install `
  -NoShortcuts `
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
  -NoShortcuts `
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
  -NoShortcuts

Assert-Missing (Join-Path $install "auto-note-gui.bat")
Assert-Missing (Join-Path $install "src")
Assert-Exists $article
Assert-Exists (Join-Path $install ".auto-note")

& (Join-Path $source "scripts\uninstall-auto-note.ps1") `
  -InstallDir $install `
  -RemoveUserData `
  -NoShortcuts

Assert-Missing $install

Write-Host "install/uninstall smoke OK"
