# Run Objective E Python test suite (Windows-native)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
