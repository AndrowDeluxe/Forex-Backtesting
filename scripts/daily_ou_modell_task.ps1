# Runs daily via Windows Task Scheduler (task "OU-Modell-DailyLog"), ~10min
# after the OU-Modell bot's last scan (21:30) - collects the day's summary
# and publishes it to the "Live Logs" Streamlit page by committing/pushing
# to the public GitHub repo, fully unattended. Set up 2026-07-29 for about
# a month of daily data before the planned performance evaluation.
#
# The Python collector already degrades gracefully (best-effort) if MT5 or
# the bot's log folder aren't reachable - this script never treats that as
# fatal, it just logs it. Every run is appended to ou_modell_logs\task_run.log
# so failures (e.g. a git push rejected for lacking cached credentials) are
# visible without needing to babysit the task.

$repo = "C:\Users\andre\Forex-Backtesting"
$logFile = Join-Path $repo "ou_modell_logs\task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
Log "=== Task gestartet ==="

try {
    $out = & python scripts\collect_ou_modell_daily_log.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Collector-Fehler: $_"
}

& git add ou_modell_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "OU-Modell: daily log $today" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== Task beendet ==="
