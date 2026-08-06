# Runs hourly via Windows Task Scheduler (task "OU-Modell-ScannerHourly"), mirrors
# scripts\daily_ou_modell_task.ps1's pattern: run the local scan, commit+push ONLY
# its own output, fully unattended. Keeps app_pages/ou_scanner.py's "Live-Signale"
# page fresh without ever needing a live yfinance call from Streamlit Cloud (same
# "collector runs locally, page only reads committed data" discipline as the rest
# of this project). Set up 2026-08-06 on user request ("Scan direkt stuendlich
# durchfuehren").
#
# scanner.py already degrades gracefully per-market (skips a market on empty
# data rather than crashing the whole scan) - this wrapper never treats a
# partial result as fatal, it just logs it.

$repo = "C:\Users\andre\Forex-Backtesting"
$scannerDir = Join-Path $repo "ou_paper_backtest"
$logFile = Join-Path $scannerDir "results\scanner_task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
Log "=== Scanner-Task gestartet ==="

try {
    Set-Location $scannerDir
    $out = & python scanner.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Scanner-Fehler: $_"
} finally {
    Set-Location $repo
}

& git add ou_paper_backtest\results\scanner_signals.csv ou_paper_backtest\results\scanner_task_run.log 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "OU-Modell Scanner: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== Scanner-Task beendet ==="
