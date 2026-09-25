# Create a workload + multi-queue config, then run multi-queue-sim.
# Usage (from multi-queue-sim/):
#   .\scripts\run-queue.ps1
#   .\scripts\run-queue.ps1 -Queues 3 -Interval 0:9 -Dist fixed -FixedWork 20

param(
  [string]$OutDir = "",
  [int]$Queues = 2,
  [string]$Interval = "0:9",
  [ValidateSet("fixed", "uniform", "normal", "geometric", "poisson")]
  [string]$Dist = "fixed",
  [int]$Seed = 42,
  [int]$FixedWork = 20,
  [int]$FixedTasks = 1,
  [int]$FixedJobs = 1,
  [double]$Lam = 1.5
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Maker = Join-Path $Root "..\make-queue-inputs\make_queue_inputs.py"
if (-not $OutDir) {
  $OutDir = Join-Path $Root "runs\queue"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

Write-Host "==> 1/2 Create workload and config"
& $Python $Maker `
  --out-dir $OutDir `
  --queues $Queues `
  --interval $Interval `
  --dist $Dist `
  --seed $Seed `
  --fixed-work $FixedWork `
  --fixed-tasks $FixedTasks `
  --fixed-jobs $FixedJobs `
  --lam $Lam

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

$Conf = Join-Path $OutDir "qconf.csv"
$Qmet = Join-Path $OutDir "qmet.csv"
$Events = Join-Path $OutDir "events.log"

Write-Host "==> 2/2 Run multi-queue-sim"
Push-Location $OutDir
try {
  & $Bin --config $Conf --qmet $Qmet --events $Events
} finally {
  Pop-Location
}

Write-Host "Done. Artifacts in $OutDir"
Get-ChildItem $OutDir | Format-Table Name, Length
