param(
  [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "auto-note"),
  [switch]$RemoveUserData,
  [switch]$NoShortcuts
)

$ErrorActionPreference = "Stop"

function Get-NormalizedPath([string]$Path) {
  return [System.IO.Path]::GetFullPath($Path)
}

function Assert-SafeInstallDir([string]$Path) {
  $normalized = Get-NormalizedPath $Path
  $root = [System.IO.Path]::GetPathRoot($normalized)
  if ($normalized.TrimEnd('\') -eq $root.TrimEnd('\')) {
    throw "InstallDir must not be a drive root: $normalized"
  }
  return $normalized
}

function Assert-UnderPath([string]$Child, [string]$Parent) {
  $childPath = Get-NormalizedPath $Child
  $parentPath = (Get-NormalizedPath $Parent).TrimEnd('\')
  if (-not $childPath.StartsWith($parentPath + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove a path outside the install directory: $childPath"
  }
}

function Remove-ChildPath([string]$Base, [string]$Name) {
  $target = Join-Path $Base $Name
  Assert-UnderPath $target $Base
  if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
    Write-Host "Removed: $target"
  }
}

function Remove-KnownShortcut([string]$Path) {
  if ((Test-Path $Path) -and ([System.IO.Path]::GetExtension($Path) -ieq ".lnk")) {
    Remove-Item -LiteralPath $Path -Force
    Write-Host "Removed shortcut: $Path"
  }
}

$install = Assert-SafeInstallDir $InstallDir
if (-not (Test-Path $install)) {
  Write-Host "auto-note is not installed at: $install"
  exit 0
}

$appDirectories = @("src", "scripts", "shortcuts", "docs", "tests", "examples", ".venv")
foreach ($name in $appDirectories) {
  Remove-ChildPath $install $name
}

$appFiles = @("auto-note-gui.bat", "README.md", "pyproject.toml", "auto-note.lnk", "auto-note GUI.lnk")
foreach ($name in $appFiles) {
  Remove-ChildPath $install $name
}

if ($RemoveUserData) {
  Remove-ChildPath $install "articles"
  Remove-ChildPath $install ".auto-note"
}

$desktop = [Environment]::GetFolderPath("DesktopDirectory")
$programs = [Environment]::GetFolderPath("Programs")
if (-not $NoShortcuts) {
  Remove-KnownShortcut (Join-Path $desktop "auto-note.lnk")
  Remove-KnownShortcut (Join-Path $programs "auto-note.lnk")
  Remove-KnownShortcut (Join-Path $programs "auto-note uninstall.lnk")
}

$remaining = @(Get-ChildItem -LiteralPath $install -Force -ErrorAction SilentlyContinue)
if ($remaining.Count -eq 0) {
  Remove-Item -LiteralPath $install -Force
  Write-Host "Removed empty install directory: $install"
} else {
  Write-Host ""
  Write-Host "User data was kept at:"
  Write-Host $install
  Write-Host "Use -RemoveUserData only when you intentionally want to delete articles and settings."
}

Write-Host ""
Write-Host "auto-note uninstalled."
