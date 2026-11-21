# Runs via Windows Task Scheduler ("News-Sources-Ledger", taeglich 22:30) - Plan 2026-11-21 (Prosper Lektion 5):
# holt alle News-/Sentiment-Quellen (inkl. Alpha Vantage), Claude ordnet die Texte ein, Werte je Quelle ins
# Forward-Ledger (fusion_lab/news_sources/ledger/). Nur Research, keine Orders, kein echtes Geld.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\news_sources"
$logFile = Join-Path $logDir "task.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
try {
    $out = & python -m fusion_lab.news_sources record 2>&1
    $out | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log "Record-Exitcode $LASTEXITCODE" }
} catch {
    Log "Record-Fehler: $_"
}

. (Join-Path $repo "scripts\lib\git_sync_push.ps1")
& git add fusion_lab\news_sources\ledger\ 2>&1 | ForEach-Object { Log $_ }
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "News-Quellen: Ledger $today" 2>&1 | ForEach-Object { Log $_ }
    Sync-AndPush -Log ${function:Log}
}
