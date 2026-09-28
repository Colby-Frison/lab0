# Run multi-queue-sim on an existing Obj A workload CSV.
# Usage:
#   .\scripts\run-existing.ps1
#   .\scripts\run-existing.ps1 -Workload ..\..\..\examples\obj-a\wl-poisson.csv
#
# Writes a two-queue qconf: q0 (Sub-10, no sink) forwards to q1 (Sub-10* -> out1.wl).

param(
  [string]$Workload = "",
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Repo = Resolve-Path (Join-Path $Root "..\..\..\..")

if (-not $Workload) {
  $Workload = Join-Path $Repo "src\examples\obj-a\wl-uniform.csv"
}
if (-not $OutDir) {
  $OutDir = Join-Path $Root "runs\existing"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (-not (Test-Path $Workload)) {
  throw "workload not found: $Workload"
}

$WlAbs = (Resolve-Path $Workload).Path
$Sink = Join-Path $OutDir "out1.wl"
$Qmet = Join-Path $OutDir "qmet.csv"
$Events = Join-Path $OutDir "events.log"
$Conf = Join-Path $OutDir "qconf.csv"

$confText = @"
Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
q0,16,1,Sub-10,10,$WlAbs,,[],[q1]
q1,8,1,Sub-10*,10,,$Sink,[q0],[]
"@
[System.IO.File]::WriteAllText($Conf, $confText)

$Bin = Join-Path $Root "build\multi-queue-sim.exe"
if (-not (Test-Path $Bin)) {
  $BinAlt = Join-Path $Root "build\multi-queue-sim"
  if (Test-Path $BinAlt) { $Bin = $BinAlt }
}
if (-not (Test-Path $Bin)) {
  Write-Host "Building multi-queue-sim..."
  cmake -S $Root -B (Join-Path $Root "build")
  cmake --build (Join-Path $Root "build")
  $Bin = Join-Path $Root "build\multi-queue-sim.exe"
}

Write-Host "Workload: $WlAbs"
Write-Host "Config:   $Conf"
Push-Location $OutDir
try {
  & $Bin --config $Conf --qmet $Qmet --events $Events
} finally {
  Pop-Location
}

Write-Host "Wrote:"
Write-Host "  $Conf"
Write-Host "  $Sink"
Write-Host "  $Qmet"
Write-Host "  $Events"
