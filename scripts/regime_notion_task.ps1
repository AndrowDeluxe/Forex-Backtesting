# Windows Task Scheduler wrapper: woechentliche Regimekarte (Wachstum x Inflation)
# neu rechnen und ins Notion-Cockpit schreiben. Reiner Daten-/Anzeige-Task:
# kein Handel, keine Bridge, kein git commit.
#   1. python -m fusion_lab.macro_regime --refresh       (FRED/ALFRED + yfinance neu)
#   2. python -m fusion_lab.notion.sync_regime           (Regime-Roadmap, Makro-Übersicht)
#   3. python -m fusion_lab.notion.sync_regime_assets --refresh  (Seite "Assets je Regime", yfinance neu)

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "regime_notion_sync.log"

function Log($msg) {
    Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== Regime-Notion-Sync gestartet ==="

foreach ($step in @("fusion_lab.macro_regime --refresh", "fusion_lab.notion.sync_regime", "fusion_lab.notion.sync_regime_assets --refresh")) {
    try {
        $out = & python -m ($step -split ' ') 2>&1
        $out | Select-Object -Last 3 | ForEach-Object { Log "[$step] $_" }
        if ($LASTEXITCODE -ne 0) { Log "[$step] Exit-Code $LASTEXITCODE -- Abbruch"; break }
    } catch {
        Log "[$step] Fehler: $_"; break
    }
}
Log "=== Regime-Notion-Sync beendet ==="
