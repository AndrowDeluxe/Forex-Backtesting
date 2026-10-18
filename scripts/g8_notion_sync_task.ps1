# Windows Task Scheduler wrapper fuer den taeglichen G8-Staerke-Abgleich ins
# Notion-Cockpit (fusion_lab/notion/sync_g8.py, DB "💱 G8-Stärke").
# Reiner Daten-/Anzeige-Task: kein Handel, keine Bridge, kein git commit.
# Laedt FRED neu (--refresh), schreibt die letzten 10 FRED-Tage + juengere
# Dukascopy-Tage + die SMH-Tabellen (idempotent, ueber "Datum · Quelle").

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "g8_notion_sync.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== G8-Notion-Sync gestartet ==="

try {
    $out = & python -m fusion_lab.notion.sync_g8 --days 10 --refresh 2>&1
    $out | Where-Object { $_ -notmatch "DUKASCRIPT" } | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log "Exit-Code $LASTEXITCODE" }
} catch {
    Log "Sync-Fehler: $_"
}

Log "=== G8-Notion-Sync beendet ==="
