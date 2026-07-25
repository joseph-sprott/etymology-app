<#
.SYNOPSIS
Live end-to-end check: POST a word to the running local Etymology Analyzer
and print the per-word result, so a regen isn't declared done on the
regression script alone.

Deterministic mechanics (the POST, the status check, the parsing) --
extracted 2026-07-24 from a hand-typed Invoke-WebRequest snippet repeated
in the etymology-regen skill. The one thing that stays AI judgment is
WHICH word to pass -- pick whatever word the change was actually about.

.PARAMETER Word
The word (or short phrase) to analyze.

.EXAMPLE
powershell -File .claude\skills\etymology-regen\scripts\http_smoke_test.ps1 -Word "consistency"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Word
)

try {
    $resp = Invoke-WebRequest -Uri "http://localhost:5000/" -Method Post `
        -Body @{ form = "analyze"; text = $Word; mode = "direct"; word_sort = "input" } `
        -UseBasicParsing -TimeoutSec 15
} catch {
    Write-Output "FAIL: request to http://localhost:5000/ errored -- is the server actually running? ($_)"
    exit 1
}

if ($resp.StatusCode -ne 200) {
    Write-Output "FAIL: got HTTP $($resp.StatusCode), expected 200"
    exit 1
}

if ($resp.Content -match '(?s)<h3>Per word</h3>.*?</div>') {
    Write-Output "OK: HTTP 200. Per-word output:"
    Write-Output $matches[0]
} else {
    Write-Output "FAIL: HTTP 200 but no 'Per word' section found in the response body -- page structure may have changed, or the word produced no output."
    exit 1
}
