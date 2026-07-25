<#
.SYNOPSIS
Stop whatever is bound to port 5000 (the Etymology Analyzer's local Flask
dev server), if anything.

Deterministic, no AI judgment involved -- extracted 2026-07-24 from prose
instructions repeated in the etymology-regen skill. Encodes two Windows
quirks confirmed directly while writing this script (not just from
CLAUDE.md's prose description -- verified live against a real running
server):
  1. A stale `Listen`-state table entry can keep reporting an OwningProcess
     that is already dead (confirmed: Get-Process on that PID returns
     nothing) for several seconds after Stop-Process succeeded.
  2. A LEFTOVER, UNRELATED `TimeWait`-state entry on the same port can
     report OwningProcess = 0 (the System Idle Process, which always
     "exists" and is never a real listener) -- this is not a live server
     and must not be treated as one. The first version of this script
     didn't filter by connection State and got fooled by this into
     reporting a false "still alive" warning after a successful stop.
  Only `Listen`-state rows are ever treated as "a real server is running
  here"; only those PIDs are targeted for Stop-Process.

.EXAMPLE
powershell -File .claude\skills\etymology-regen\scripts\stop_dev_server.ps1
#>

$listeners = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Write-Output "Nothing is listening on port 5000. Nothing to stop."
    exit 0
}

foreach ($c in $listeners) {
    $procId = $c.OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Output "Stopping PID $procId ($($proc.ProcessName)) listening on port 5000..."
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    } else {
        Write-Output "Port 5000 shows PID $procId listening, but that process is already dead -- the documented stale-table-entry quirk, not a real conflict."
    }
}

Start-Sleep -Milliseconds 750
$stillListening = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
$stillAlive = $stillListening | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
if ($stillAlive) {
    Write-Output "WARNING: a process is genuinely still alive and listening on port 5000 -- re-check Get-NetTCPConnection -State Listen, do not assume the PID above was the only one (Werkzeug's debug-mode reloader can spawn a child that a single Stop-Process on the parent doesn't reach)."
    exit 1
}
Write-Output "Port 5000 is free (or shows only a stale/dead table entry, which is safe to ignore). Safe to start a new server."
exit 0
