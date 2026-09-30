# Run the Obj C Python test suite (Windows-native).
# Usage (from obj-c/):
#   .\run-all-tests.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root "../../../.venv/Scripts/python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

Write-Host "==> Obj C tests (including histogram and scatter plots)"
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "==> all tests finished"
