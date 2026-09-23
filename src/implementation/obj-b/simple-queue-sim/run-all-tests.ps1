# Build and run the simple-queue-sim CTest suite (Windows-native).
# Usage (from simple-queue-sim/):
#   .\run-all-tests.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "==> cmake configure"
cmake -S . -B build
Write-Host "==> cmake build"
cmake --build build
Write-Host "==> ctest"
ctest --test-dir build --output-on-failure
Write-Host "==> all tests finished"
