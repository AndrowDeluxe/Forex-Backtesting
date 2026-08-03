# Runs daily via Windows Task Scheduler ("ORB-ForwardTest-DailyLog") -
# collects the day's ORB forward-test summary and publishes it to the
# "Live Logs > ORB Forward-Test" Streamlit page by committing/pushing to
# the public GitHub repo, unattended. Mirrors daily_ou_modell_task.ps1.
#
# collect_orb_forward_test_log.py degrades gracefully (best-effort) if MT5
# or the forward-test's log folder aren't reachable - this script never
# treats that as fatal, it just logs it.

$repo = "C:\Users\andre\Forex-Backtesting"
$logFile = Join-Path $repo "orb_forward_test_logs\task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
Log "=== Task gestartet ==="

try {
    $out = & python scripts\collect_orb_forward_test_log.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Collector-Fehler: $_"
}

& git add orb_forward_test_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "ORB Forward-Test: daily log $today" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== Task beendet ==="
