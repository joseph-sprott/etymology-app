<#
.SYNOPSIS
  Build etymology.db and verify it, as one command.

.DESCRIPTION
  Encodes the operational traps that made this a repeated manual dance during
  the 2026-07-26 rework -- each one cost a full ten-minute build at least once:

    * a foreground/background tool call is capped at 10 minutes and kills the
      build seconds before it finishes, so it is launched DETACHED
    * `Get-Process python` finds nothing (the Store build reports as
      `python3.13`), so process checks use CIM and match on command line
    * the swap cannot replace a file the running app holds open; the build
      leaves the finished database at .new rather than discarding it
    * a stale .new from a crashed run must not be mistaken for a fresh build

.EXAMPLE
  powershell -File scripts\build.ps1
  powershell -File scripts\build.ps1 -Sample 20000     # fast dev copy
  powershell -File scripts\build.ps1 -SkipVerify
#>
param(
  [int]$Sample = 0,
  [string[]]$Words = @(),
  [switch]$SkipVerify,
  [switch]$Force          # build even if app.py is running
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$log  = Join-Path $env:TEMP "etymology_build"
$outLog = "$log.out.log"; $errLog = "$log.err.log"

# --- 1. Is the app holding the database open? -------------------------------
$running = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" |
             Where-Object { $_.CommandLine -match "app\.py" })
if ($running -and -not $Force) {
  Write-Host "app.py is running (PID $($running.ProcessId -join ', '))." -ForegroundColor Yellow
  Write-Host "The final swap will be blocked and the build left at etymology.db.new."
  Write-Host "Stop it first, or re-run with -Force to build anyway."
  Write-Host ""
}

# --- 2. Clear any stale scratch build ---------------------------------------
$new = Join-Path $root "etymology.db.new"
if (Test-Path $new) {
  Write-Host "removing stale $new"
  Remove-Item $new -Force
}

# --- 3. Launch detached ------------------------------------------------------
$argList = @("build_etymology_db.py")
if ($Sample -gt 0)  { $argList += @("--sample", "$Sample") }
if ($Words.Count)   { $argList += @("--words") + $Words }

Write-Host "building: python $($argList -join ' ')"
$proc = Start-Process -FilePath "python" -ArgumentList $argList `
          -WorkingDirectory $root -RedirectStandardOutput $outLog `
          -RedirectStandardError $errLog -WindowStyle Hidden -PassThru

$sw = [Diagnostics.Stopwatch]::StartNew()
while (-not $proc.HasExited) {
  Start-Sleep -Seconds 15
  $tail = (Get-Content $errLog -Tail 1 -ErrorAction SilentlyContinue)
  Write-Host ("  [{0,5:n0}s] {1}" -f $sw.Elapsed.TotalSeconds, $tail)
}
$sw.Stop()

Get-Content $outLog | Select-String -Pattern "status_|etymologies|surface_|compound_splits|=== validators|PASS|FAIL"
Get-Content $errLog | Select-String -Pattern "done in|could not replace|swapping"

if ($proc.ExitCode -ne 0) {
  Write-Host "build exited $($proc.ExitCode)" -ForegroundColor Red
  if (Test-Path $new) {
    Write-Host "finished database left at $new -- stop app.py and rename it." -ForegroundColor Yellow
  }
  exit $proc.ExitCode
}

# --- 4. Verify ---------------------------------------------------------------
if (-not $SkipVerify) {
  Write-Host ""
  Write-Host "verifying..."
  & python (Join-Path $root "scripts\verify.py")
  exit $LASTEXITCODE
}
