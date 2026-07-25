param(
    [string]$RepoPath = "C:\Users\Josep\Desktop\Etymology Project\etymology-app",
    [string]$BackupDir = "$env:TEMP\etymology-sync-backups",
    [string]$Branch = ""
)

# Deliberately NOT using $ErrorActionPreference = "Stop": git writes routine
# progress text (e.g. fetch's "From https://...") to stderr even on success,
# and under "Stop" that gets promoted from a non-terminating to a terminating
# error and kills the script on a clean run. Use $LASTEXITCODE to check real
# failures instead.

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $RepoPath

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = (git branch --show-current).Trim()
}

Write-Host "== git status before sync =="
git status --short

Write-Host "== git fetch origin =="
git fetch origin
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: git fetch failed (exit $LASTEXITCODE)"
    exit 1
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$pullOutput = git pull --ff-only origin $Branch 2>&1 | Out-String
$pullExit = $LASTEXITCODE

if ($pullExit -ne 0 -and $pullOutput -match "untracked working tree files would be overwritten") {
    Write-Host "Untracked-file conflict detected -- backing up before retrying."
    $lines = $pullOutput -split "`r?`n"
    $conflicting = @()
    $inList = $false
    foreach ($line in $lines) {
        if ($line -match "untracked working tree files would be overwritten") { $inList = $true; continue }
        if ($inList) {
            if ($line -match "^\s*(.+\S)\s*$" -and $line -notmatch "Please move or remove") {
                $conflicting += $Matches[1].Trim()
            } else {
                break
            }
        }
    }

    if ($conflicting.Count -eq 0) {
        Write-Host "FAIL: conflict detected but could not parse filenames from git output. Raw output:"
        Write-Host $pullOutput
        exit 1
    }

    $backedUp = @{}
    foreach ($f in $conflicting) {
        $src = Join-Path $RepoPath $f
        if (Test-Path $src) {
            $destName = "$stamp-" + ($f -replace '[\\/]', '_')
            $dest = Join-Path $BackupDir $destName
            Copy-Item $src $dest -Force
            $backedUp[$f] = $dest
            Write-Host "Backed up: $f -> $dest"
        }
    }

    Write-Host "== retrying git pull --ff-only =="
    $pullOutput = git pull --ff-only origin $Branch 2>&1 | Out-String
    $pullExit = $LASTEXITCODE
    Write-Host $pullOutput

    if ($pullExit -eq 0) {
        foreach ($f in $backedUp.Keys) {
            $newPath = Join-Path $RepoPath $f
            $backupPath = $backedUp[$f]
            if (Test-Path $newPath) {
                $diff = Compare-Object (Get-Content $backupPath) (Get-Content $newPath)
                if ($diff) {
                    Write-Host "DIFFERS: $f -- local backup and pulled version are NOT identical. Backup kept at $backupPath. Manual review required before discarding the backup."
                } else {
                    Write-Host "IDENTICAL: $f -- local and pulled versions match byte-for-byte. Safe to leave the backup untouched (not auto-deleted)."
                }
            } else {
                Write-Host "WARNING: $f no longer present after pull -- backup kept at $backupPath."
            }
        }
    }
} else {
    Write-Host $pullOutput
}

if ($pullExit -ne 0) {
    Write-Host "FAIL: git pull --ff-only did not succeed (exit $pullExit). Do not force -- investigate the output above."
    exit 1
}

Write-Host "== git log -3 =="
git log -3 --oneline

Write-Host "== git status after sync =="
git status --short

Write-Host "OK: sync complete."
