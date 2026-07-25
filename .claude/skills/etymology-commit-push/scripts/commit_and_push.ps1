<#
.SYNOPSIS
Stage everything, commit with a pre-written message file, and push -- the
exact sequence used successfully throughout the 2026-07-24 session.

Deterministic mechanics only. Does NOT decide the commit message content
(that's the caller's judgment, written to a file beforehand -- see
.claude\jobs\*\tmp\ for where this session's message files lived) and does
NOT review the staged diff for you (see the skill's SKILL.md -- review
`git status`/`git diff --stat` yourself BEFORE invoking this script; it
commits and pushes in one shot with no pause to reconsider).

Uses -F <file> rather than -m "<message>" deliberately: a multi-line commit
message passed via -m through PowerShell's here-string quoting broke
mid-session (git received the message split into multiple mis-parsed
pathspec arguments) -- writing the message to a file first and using -F
sidesteps that entirely.

.PARAMETER MessageFile
Path to a file containing the full commit message (already written by the
caller).

.PARAMETER RepoPath
Path to the git repository. Defaults to this project's root.

.EXAMPLE
powershell -File .claude\skills\etymology-commit-push\scripts\commit_and_push.ps1 -MessageFile C:\path\to\msg.txt
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$MessageFile,

    [string]$RepoPath = "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
)

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Test-Path $MessageFile)) {
    Write-Output "FAIL: message file not found: $MessageFile"
    exit 1
}

Push-Location $RepoPath
try {
    git add -A
    if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: git add -A failed"; exit 1 }

    Write-Output "--- git status (staged) ---"
    git status
    if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: git status failed"; exit 1 }

    git commit -F $MessageFile
    if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: git commit failed"; exit 1 }

    git push
    if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: git push failed"; exit 1 }

    Write-Output "--- git log (last 3) ---"
    git log --oneline -3
    Write-Output "OK: committed and pushed."
} finally {
    Pop-Location
}
