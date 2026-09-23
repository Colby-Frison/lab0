# Run simple-queue-sim on an existing Obj A workload CSV.
# Usage:
#   .\scripts\run-existing.ps1 [-Workload PATH] [-OutDir PATH]
#
# Default workload: src/examples/obj-a/wl-uniform.csv

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
$Sink = Join-Path $OutDir "out0.wl"
$Qmet = Join-Path $OutDir "qmet.csv"
$Events = Join-Path $OutDir "events.log"
$Conf = Join-Path $OutDir "qconf.csv"

# Prefer Sub-10* so multi-task jobs drain to the sink.
$confText = @"
Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
q0,64,1,Sub-10*,10,$WlAbs,$Sink,[],[]
"@
[System.IO.File]::WriteAllText($Conf, $confText)
$Bin = Join-Path $Root "build\simple-queue-sim.exe"
if (-not (Test-Path $Bin)) {
  $BinAlt = Join-Path $Root "build\simple-queue-sim"
  if (Test-Path $BinAlt) { $Bin = $BinAlt }
}

if (-not (Test-Path $Bin)) {
  Write-Host "Building simple-queue-sim..."
  cmake -S $Root -B (Join-Path $Root "build")
  cmake --build (Join-Path $Root "build")
  if (-not (Test-Path $Bin)) {
    $Bin = Join-Path $Root "build\simple-queue-sim.exe"
  }
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
Write-Host "  $Sink"
Write-Host "  $Qmet"
Write-Host "  $Events"
