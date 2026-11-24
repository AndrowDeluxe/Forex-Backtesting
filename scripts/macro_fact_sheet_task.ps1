# Windows Task Scheduler wrapper: Makro Fact Sheet erzeugen (Datei + Notion) und Forecast-Ledger fuellen.
# Reiner Analyse-Task: kein Handel, keine Bridge, kein git commit.
# Laeuft werktags 07:45, nach "Makro-Daten" (07:30, ~3 Min.). Seit 24.11.2026 (Nutzerentscheid:
# Fact Sheet v4 vollstaendig -> taeglich laufen lassen, damit das Ledger vorwaerts prueft).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "macro_fact_sheet.log"

function Log($msg) {
    Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
$code = 1
Log "=== Makro-Fact-Sheet gestartet ==="
try {
    $out = & python -m fusion_lab.macro_agent --notion 2>&1
    $code = $LASTEXITCODE
    $out | Where-Object { "$_" -notmatch "DUKASCRIPT" } | ForEach-Object { Log "$_" }
    Log "Exit-Code $code"
} catch {
    Log "Fehler: $_"
}
Log "=== Makro-Fact-Sheet beendet ==="
exit $code
