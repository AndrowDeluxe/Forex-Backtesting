# Taeglicher Lauf via Windows Task Scheduler (Task "BTC-EMA-Cross-Scan"),
# mirrors scripts\cls_practical_scan_task.ps1's Muster: lokalen Scan
# ausfuehren, NUR dessen eigenen Output (btc_ema_cross_logs/) committen+
# pushen, komplett unattended. PAPIER-Konto -- es wird nie ein echtes
# Exchange-Konto beruehrt oder eine echte Order platziert.
#
# Eingerichtet 2026-08-16 auf Anfrage des Users ("Bot bauen und forward
# testen"). collect_btc_ema_cross_daily_log.py degradiert bereits graceful
# (schreibt einen "status"-Hinweis statt zu crashen, z.B. bei Binance-API-
# Fehlern oder zu fruehem Lauf) - dieser Wrapper behandelt das nie als
# fatal, loggt es nur.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "btc_ema_cross_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== BTC-EMA-Cross-Scan-Task gestartet ==="

try {
    $out = & python scripts\collect_btc_ema_cross_daily_log.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Collector-Fehler: $_"
}

& git add btc_ema_cross_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "BTC EMA9/21 Paper-Forward-Test: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== BTC-EMA-Cross-Scan-Task beendet ==="
