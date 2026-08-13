# Runs mehrfach taeglich waehrend des Entry-Fensters via Windows Task Scheduler
# (Task "CLS-Practical-Scan"), mirrors scripts\hourly_ou_scanner_task.ps1's Muster:
# lokalen Scan ausfuehren, NUR dessen eigenen Output committen+pushen, komplett
# unattended. Haelt app_pages/cls_practical_live_log.py aktuell, ohne dass
# Streamlit Cloud selbst einen Dukascopy-Datenabruf machen muss (gleiche
# "Collector laeuft lokal, Seite liest nur committete Daten"-Disziplin wie der
# Rest des Projekts). Eingerichtet 2026-08-13 auf Anfrage des Users ("Richte
# erst den Collector Lauf ein").
#
# collect_cls_practical_daily_log.py degradiert bereits pro Tag graceful
# (schreibt einen "status"-Hinweis statt zu crashen, z.B. wenn die Settle-Range
# noch nicht vollstaendig ist) - dieser Wrapper behandelt das nie als fatal,
# loggt es nur.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "cls_practical_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== CLS-Practical-Scan-Task gestartet ==="

try {
    $out = & python scripts\collect_cls_practical_daily_log.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Collector-Fehler: $_"
}

& git add cls_practical_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "CLS Practical Scan: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== CLS-Practical-Scan-Task beendet ==="
