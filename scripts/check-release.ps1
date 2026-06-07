param(
  [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [switch]$Full,
  [switch]$SkipGuiSmoke
)

$ErrorActionPreference = "Stop"

function Invoke-Check([string]$Name, [scriptblock]$Script) {
  Write-Host ""
  Write-Host "== $Name =="
  $global:LASTEXITCODE = 0
  & $Script
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  Write-Host "[OK] $Name"
}

$project = [System.IO.Path]::GetFullPath($ProjectDir)
$venvPython = Join-Path $project ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$oldPythonPath = $env:PYTHONPATH
$oldLauncherCheck = $env:AUTO_NOTE_LAUNCHER_CHECK
$pushedLocation = $false

try {
  Push-Location $project
  $pushedLocation = $true
  $env:PYTHONPATH = Join-Path $project "src"

  Invoke-Check "Python compile" {
    & $python -m compileall src tests
  }

  Invoke-Check "Unit tests" {
    & $python -m unittest discover -s tests
  }

  Invoke-Check "Product quality gate" {
    & $python -m auto_note quality --project-dir $project --product-only
  }

  Invoke-Check "Hidden GUI launcher syntax" {
    $env:AUTO_NOTE_LAUNCHER_CHECK = "1"
    cscript.exe //nologo .\scripts\launch-gui.vbs
  }

  if (-not $SkipGuiSmoke) {
    Invoke-Check "GUI smoke" {
      & $python -m auto_note gui --project-dir $project --smoke
    }
  }

  if ($Full) {
    Invoke-Check "Privacy audit" {
      & $python -m auto_note privacy-audit --project-dir $project
    }

    Invoke-Check "Commercial readiness" {
      & $python -m auto_note commercial-readiness --project-dir $project
    }

    Invoke-Check "Preflight with GUI smoke" {
      & $python -m auto_note preflight --project-dir $project --gui-smoke
    }

    Invoke-Check "Install/uninstall smoke" {
      powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-install.ps1 -SourceDir $project
    }
  }

  Write-Host ""
  Write-Host "auto-note release check OK"
} finally {
  if ($pushedLocation) {
    Pop-Location
  }
  $env:PYTHONPATH = $oldPythonPath
  $env:AUTO_NOTE_LAUNCHER_CHECK = $oldLauncherCheck
}
