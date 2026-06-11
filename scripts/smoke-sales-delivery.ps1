param(
  [string]$SourceDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$WorkRoot = "",
  [switch]$Keep
)

$ErrorActionPreference = "Stop"

function Invoke-Smoke([string]$Name, [scriptblock]$Script) {
  Write-Host ""
  Write-Host "== $Name =="
  $global:LASTEXITCODE = 0
  & $Script
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  Write-Host "[OK] $Name"
}

function Assert-Exists([string]$Path, [string]$Message) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw $Message
  }
}

$source = [System.IO.Path]::GetFullPath($SourceDir)
if (-not (Test-Path -LiteralPath (Join-Path $source "src\auto_note\__main__.py"))) {
  throw "SourceDir does not look like an auto-note source tree: $source"
}

$providedWorkRoot = -not [string]::IsNullOrWhiteSpace($WorkRoot)
$root = if ($WorkRoot) {
  [System.IO.Path]::GetFullPath($WorkRoot)
} else {
  Join-Path ([System.IO.Path]::GetTempPath()) ("auto-note-sales-smoke-" + [guid]::NewGuid().ToString("N"))
}
$work = Join-Path $root "auto-note"

New-Item -ItemType Directory -Path $root -Force | Out-Null
if (Test-Path -LiteralPath $work) {
  Remove-Item -LiteralPath $work -Recurse -Force
}

$excludeDirs = @(".git", ".venv", ".auto-note", "__pycache__")
$excludeFiles = @("*.pyc", "*.pyo")
$robocopyArgs = @(
  $source,
  $work,
  "/E",
  "/XD"
) + $excludeDirs + @(
  "/XF"
) + $excludeFiles + @(
  "/NFL",
  "/NDL",
  "/NJH",
  "/NJS",
  "/NP"
)

& robocopy @robocopyArgs | Out-Host
if ($LASTEXITCODE -ge 8) {
  throw "Failed to copy source tree for sales delivery smoke. robocopy exit code: $LASTEXITCODE"
}
$global:LASTEXITCODE = 0

$oldPythonPath = $env:PYTHONPATH
$pushedLocation = $false

try {
  Push-Location $work
  $pushedLocation = $true
  $env:PYTHONPATH = Join-Path $work "src"

  Invoke-Smoke "Prepare sales smoke environment" {
    & cmd.exe /c ".\scripts\ensure-env.bat manual"
  }

  $python = Join-Path $work ".venv\Scripts\python.exe"
  Assert-Exists $python "Expected prepared virtualenv Python was not created."

  Invoke-Smoke "Repair smoke project" {
    & $python -m auto_note repair --project-dir . --apply
  }

  Invoke-Smoke "Seed seller settings" {
    & $python -m auto_note commercial-setup --project-dir . `
      --seller-name "Demo Shop" `
      --sales-url "https://example.com/auto-note" `
      --refund-url "https://example.com/refund" `
      --support-contact "https://example.com/support" `
      --terms-reviewed `
      --support-scope-confirmed
  }

  Invoke-Smoke "Create smoke backup" {
    & $python -m auto_note backup --project-dir .
  }

  Invoke-Smoke "Sales finalize" {
    & $python -m auto_note sales-finalize --project-dir . --no-report
  }

  $salesDir = Join-Path $work ".auto-note\sales"
  $buyerPackage = Get-ChildItem -LiteralPath $salesDir -Filter "auto-note-buyer-delivery-*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $buyerPackage) {
    throw "Sales finalize did not create a buyer delivery zip."
  }

  Invoke-Smoke "Buyer package verify" {
    & $python -m auto_note sales-handoff --verify-buyer-package $buyerPackage.FullName
  }

  Invoke-Smoke "Buyer send readiness and receipt" {
    & $python -m auto_note sales-finalize --project-dir . --send-check --send-check-report --delivery-receipt
  }

  Invoke-Smoke "Sales launch checklist and confirmation" {
    & $python -m auto_note sales-launch --project-dir . --report --confirm-preview --note "smoke preview checked"
  }

  $readinessReport = Get-ChildItem -LiteralPath $salesDir -Filter "buyer-send-readiness-*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  $deliveryReceipt = Get-ChildItem -LiteralPath $salesDir -Filter "seller-delivery-receipt-*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  $launchChecklist = Get-ChildItem -LiteralPath $salesDir -Filter "sales-launch-checklist-*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  $launchConfirmation = Get-ChildItem -LiteralPath $salesDir -Filter "sales-launch-confirmation-*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if (-not $readinessReport) {
    throw "Buyer send readiness report was not created."
  }
  if (-not $deliveryReceipt) {
    throw "Seller delivery receipt was not created."
  }
  if (-not $launchChecklist) {
    throw "Sales launch checklist was not created."
  }
  if (-not $launchConfirmation) {
    throw "Sales launch confirmation was not created."
  }
  Assert-Exists $readinessReport.FullName "Buyer send readiness report was not created."
  Assert-Exists $deliveryReceipt.FullName "Seller delivery receipt was not created."
  Assert-Exists $launchChecklist.FullName "Sales launch checklist was not created."
  Assert-Exists $launchConfirmation.FullName "Sales launch confirmation was not created."

  $launchText = Get-Content -LiteralPath $launchChecklist.FullName -Raw -Encoding UTF8
  if ($launchText -notlike "*Marketplace launch confirmation*") {
    throw "Sales launch checklist does not include marketplace launch confirmation items."
  }
  if ($launchText -notlike "*Platform-specific launch checks*") {
    throw "Sales launch checklist does not include platform-specific launch checks."
  }
  if ($launchText -notlike "*Buyer delivery copy sheet*") {
    throw "Sales launch checklist does not include buyer delivery copy values."
  }
  if ($launchText -notlike "*latest release package*") {
    throw "Sales launch checklist does not include the latest release package value."
  }
  if ($launchText -notlike "*zip SHA-256*") {
    throw "Sales launch checklist does not include the buyer ZIP SHA-256 value."
  }

  $confirmationText = Get-Content -LiteralPath $launchConfirmation.FullName -Raw -Encoding UTF8
  if ($confirmationText -notlike "*Sales launch confirmation*") {
    throw "Sales launch confirmation title was not found."
  }
  if ($confirmationText -notlike "*smoke preview checked*") {
    throw "Sales launch confirmation does not include the seller note."
  }
  if ($confirmationText -notlike "*seller-only evidence*") {
    throw "Sales launch confirmation does not include seller-only evidence guidance."
  }
  if ($confirmationText -notlike "*latest release package*") {
    throw "Sales launch confirmation does not include the latest release package value."
  }

  Write-Host ""
  Write-Host "sales delivery smoke OK"
  Write-Host "- work dir: $work"
  Write-Host "- buyer zip: $($buyerPackage.Name)"
  Write-Host "- send readiness: $($readinessReport.Name)"
  Write-Host "- seller receipt: $($deliveryReceipt.Name)"
  Write-Host "- launch checklist: $($launchChecklist.Name)"
  Write-Host "- launch confirmation: $($launchConfirmation.Name)"
} finally {
  if ($pushedLocation) {
    Pop-Location
  }
  $env:PYTHONPATH = $oldPythonPath
  if (-not $Keep) {
    if ($providedWorkRoot) {
      Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    } else {
      Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
}
