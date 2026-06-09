param(
  [string]$SourceDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "auto-note"),
  [switch]$NoShortcuts,
  [switch]$SkipEnv
)

$ErrorActionPreference = "Stop"

function Get-NormalizedPath([string]$Path) {
  return [System.IO.Path]::GetFullPath($Path)
}

function Assert-UnderPath([string]$Child, [string]$Parent) {
  $childPath = Get-NormalizedPath $Child
  $parentPath = (Get-NormalizedPath $Parent).TrimEnd('\')
  if (-not $childPath.StartsWith($parentPath + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to update a path outside the install directory: $childPath"
  }
}

function Get-ProjectVersion([string]$BaseDir) {
  $pyproject = Join-Path $BaseDir "pyproject.toml"
  if (-not (Test-Path $pyproject)) {
    return "0.0.0"
  }
  $match = Select-String -Path $pyproject -Pattern '^\s*version\s*=\s*["'']([^"'']+)["'']' | Select-Object -First 1
  if ($match -and $match.Matches.Count -gt 0) {
    return $match.Matches[0].Groups[1].Value
  }
  return "0.0.0"
}

function Get-UniquePath([string]$Path) {
  if (-not (Test-Path $Path)) {
    return $Path
  }
  $dir = Split-Path $Path -Parent
  $name = [System.IO.Path]::GetFileNameWithoutExtension($Path)
  $extension = [System.IO.Path]::GetExtension($Path)
  for ($index = 2; $index -lt 1000; $index++) {
    $candidate = Join-Path $dir ("{0}-{1:D2}{2}" -f $name, $index, $extension)
    if (-not (Test-Path $candidate)) {
      return $candidate
    }
  }
  throw "Could not create a unique backup path: $Path"
}

function Add-ZipFile([System.IO.Compression.ZipArchive]$Archive, [string]$Source, [string]$ArchiveName) {
  if (-not (Test-Path $Source)) {
    return
  }
  [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Archive, $Source, $ArchiveName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
}

function Add-ZipTree([System.IO.Compression.ZipArchive]$Archive, [string]$Root, [string]$ArchiveRoot) {
  if (-not (Test-Path $Root)) {
    return
  }
  foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -File) {
    $relative = $file.FullName.Substring((Get-NormalizedPath $Root).Length).TrimStart('\')
    $archiveName = ($ArchiveRoot + "/" + $relative.Replace('\', '/'))
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Archive, $file.FullName, $archiveName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
  }
}

function New-PreInstallBackup([string]$BaseDir) {
  $hasArticles = Test-Path (Join-Path $BaseDir "articles")
  $hasSettings = Test-Path (Join-Path $BaseDir ".auto-note\settings.json")
  $hasIdeas = Test-Path (Join-Path $BaseDir ".auto-note\ideas.json")
  if (-not ($hasArticles -or $hasSettings -or $hasIdeas)) {
    return $null
  }

  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $backupDir = Join-Path $BaseDir ".auto-note\install-backups"
  New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
  $backupPath = Get-UniquePath (Join-Path $backupDir ("auto-note-preinstall-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".zip"))
  $archive = [System.IO.Compression.ZipFile]::Open($backupPath, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    Add-ZipTree $archive (Join-Path $BaseDir "articles") "articles"
    Add-ZipFile $archive (Join-Path $BaseDir ".auto-note\settings.json") ".auto-note/settings.json"
    Add-ZipFile $archive (Join-Path $BaseDir ".auto-note\ideas.json") ".auto-note/ideas.json"
  } finally {
    $archive.Dispose()
  }
  return $backupPath
}

function Write-InstallInfo([string]$BaseDir, [string]$SourceDir, [string]$Version, [string]$BackupPath) {
  $infoPath = Join-Path $BaseDir ".auto-note\install-info.json"
  $backupName = $null
  if ($BackupPath) {
    $backupName = Split-Path $BackupPath -Leaf
  }
  $info = [ordered]@{
    installed_at = (Get-Date).ToString("s")
    version = $Version
    source = $SourceDir
    preinstall_backup = $backupName
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $infoPath -Parent) | Out-Null
  $info | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $infoPath -Encoding UTF8
}

$source = Get-NormalizedPath $SourceDir
$install = Get-NormalizedPath $InstallDir
$installRoot = [System.IO.Path]::GetPathRoot($install)
if (-not (Test-Path (Join-Path $source "auto-note-gui.bat"))) {
  throw "auto-note-gui.bat was not found in source: $source"
}
if ($source -eq $install) {
  throw "SourceDir and InstallDir must be different."
}
if ($install.TrimEnd('\') -eq $installRoot.TrimEnd('\')) {
  throw "InstallDir must not be a drive root: $install"
}

New-Item -ItemType Directory -Force -Path $install | Out-Null
$version = Get-ProjectVersion $source
$preInstallBackup = New-PreInstallBackup $install

$directories = @("src", "scripts", "shortcuts", "docs", "tests", "examples")
foreach ($name in $directories) {
  $from = Join-Path $source $name
  if (-not (Test-Path $from)) {
    continue
  }
  $to = Join-Path $install $name
  Assert-UnderPath $to $install
  if (Test-Path $to) {
    Remove-Item -LiteralPath $to -Recurse -Force
  }
  Copy-Item -LiteralPath $from -Destination $to -Recurse -Force
}

$files = @("auto-note-gui.bat", "README.md", "pyproject.toml")
foreach ($name in $files) {
  $from = Join-Path $source $name
  if (Test-Path $from) {
    Copy-Item -LiteralPath $from -Destination (Join-Path $install $name) -Force
  }
}

New-Item -ItemType Directory -Force -Path (Join-Path $install "articles") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $install ".auto-note") | Out-Null
Write-InstallInfo $install $source $version $preInstallBackup

if (-not $NoShortcuts) {
  $desktop = [Environment]::GetFolderPath("DesktopDirectory")
  $programs = [Environment]::GetFolderPath("Programs")
  $shortcutScript = Join-Path $install "scripts\create-gui-shortcut.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript `
    -ProjectDir $install `
    -ShortcutPath (Join-Path $desktop "auto-note.lnk") `
    -SafeDisplayShortcutPath (Join-Path $desktop "auto-note safe display.lnk")
  & powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript `
    -ProjectDir $install `
    -ShortcutPath (Join-Path $programs "auto-note.lnk") `
    -SafeDisplayShortcutPath (Join-Path $programs "auto-note safe display.lnk")

  $shell = New-Object -ComObject WScript.Shell
  $uninstallShortcut = $shell.CreateShortcut((Join-Path $programs "auto-note uninstall.lnk"))
  $uninstallShortcut.TargetPath = (Join-Path $install "shortcuts\uninstall-auto-note.bat")
  $uninstallShortcut.WorkingDirectory = $install
  $uninstallShortcut.Description = "Uninstall auto-note"
  $uninstallShortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,84"
  $uninstallShortcut.WindowStyle = 1
  $uninstallShortcut.Save()
}

if (-not $SkipEnv) {
  & (Join-Path $install "scripts\ensure-env.bat") manual
}

Write-Host ""
Write-Host "auto-note installed."
Write-Host "Install directory: $install"
Write-Host "Version: $version"
if ($preInstallBackup) {
  Write-Host "Pre-install backup: $preInstallBackup"
}
Write-Host "Open auto-note from the desktop shortcut, Start menu shortcut, or:"
Write-Host (Join-Path $install "auto-note-gui.bat")
