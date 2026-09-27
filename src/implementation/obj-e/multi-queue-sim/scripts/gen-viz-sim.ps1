# Generate a workload (Obj A), visualize it, write a two-queue config, then run multi-queue-sim.
# Usage:
#   .\scripts\gen-viz-sim.ps1
#   .\scripts\gen-viz-sim.ps1 -Interval 0:9 -Dist fixed -FixedWork 20 -Seed 1
#
# q0 applies Sub-10 once and forwards leftover work to q1.
# q1 finishes with Sub-10* and writes out1.wl.

param(
  [string]$Interval = "0:9",
  [ValidateSet("fixed", "uniform", "normal", "geometric", "poisson")]
  [string]$Dist = "fixed",
  [double]$Lam = 1.5,
  [int]$Seed = 42,
  [ValidateSet("fixed", "dist")]
  [string]$TaskMode = "fixed",
  [int]$FixedTasks = 1,
  [int]$FixedWork = 20,
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Repo = Resolve-Path (Join-Path $Root "..\..\..\..")
$Gen = Join-Path $Repo "src\implementation\obj-a\workload-generator\workload_generator.py"
$Viz = Join-Path $Repo "src\implementation\obj-a\workload-visualizer\workload_visualizer.py"

if (-not $OutDir) {
  $OutDir = Join-Path $Root "runs\pipeline"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Wl = Join-Path $OutDir "in0.wl"
$Hist = Join-Path $OutDir "hist_arrival.png"
$Scat = Join-Path $OutDir "scat_arrival_tasks.png"
$Sink = Join-Path $OutDir "out1.wl"
$Qmet = Join-Path $OutDir "qmet.csv"
$Events = Join-Path $OutDir "events.log"
$Conf = Join-Path $OutDir "qconf.csv"

$Python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

Write-Host "==> 1/3 Generate workload"
$genArgs = @(
  $Gen,
  "--interval", $Interval,
  "--dist", $Dist,
  "--seed", "$Seed",
  "--task-mode", $TaskMode,
  "--fixed-tasks", "$FixedTasks",
  "--fixed-work", "$FixedWork",
  "--out", $Wl
)
if ($Dist -eq "poisson") { $genArgs += @("--lam", "$Lam") }
if ($Dist -eq "uniform") { $genArgs += @("--low", "1", "--high", "3") }
if ($Dist -eq "normal") { $genArgs += @("--mu", "2", "--sigma", "1") }
if ($Dist -eq "geometric") { $genArgs += @("--p", "0.4") }
if ($Dist -eq "fixed") { $genArgs += @("--fixed-jobs", "1") }

& $Python @genArgs

Write-Host "==> 2/3 Visualize workload"
& $Python $Viz $Wl --hist "arrival time" --bins 15 --title "Arrivals ($Dist)" --out $Hist
& $Python $Viz $Wl --scat "arrival time,Job Id" --title "Jobs over time" --out $Scat

$WlAbs = (Resolve-Path $Wl).Path
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

Write-Host "==> 3/3 Run multi-queue-sim"
Push-Location $OutDir
try {
  & $Bin --config $Conf --qmet $Qmet --events $Events
} finally {
  Pop-Location
}

Write-Host "Done. Artifacts in $OutDir"
Get-ChildItem $OutDir | Format-Table Name, Length
