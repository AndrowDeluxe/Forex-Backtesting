# Windows Task Scheduler wrapper: Daten fuer die CTNL-Makro-Sperre (gold_smc_htf_ltf/macro_gate.py).
# Laedt FRED + yfinance neu und baut fusion_lab/data/gold_confirm/score_frame.parquet.
# Reiner Daten-Task: kein Handel, kein git commit. Faellt er aus, laesst die Sperre nach 5 Tagen
# alles durch (fail-safe) und meldet das im Bridge-Log. Seit 2026-11-15 (Nutzerentscheid).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "gold_macro_gate_refresh.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8 }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== Gold-Makro-Gate-Refresh gestartet ==="
try {
    $out = & python -W ignore -m fusion_lab.gold_confirm.refresh 2>&1
    $out | ForEach-Object { Log "$_" }
    Log "Exit-Code $LASTEXITCODE"
} catch {
    Log "Fehler: $_"
}
Log "=== Gold-Makro-Gate-Refresh beendet ==="
