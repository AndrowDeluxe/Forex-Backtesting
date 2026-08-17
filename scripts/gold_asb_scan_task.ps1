# Analog zu scripts\cls_practical_scan_task.ps1: lokalen Collector ausfuehren,
# NUR dessen eigenen Output (gold_asb_logs\) committen+pushen, komplett
# unattended. Haelt app_pages/gold_asb_live_log.py aktuell, ohne dass
# Streamlit Cloud selbst Zugriff auf GoldASB-MT5-Bridge/state/*.sqlite3
# braucht (gleiche "Collector laeuft lokal, Seite liest nur committete
# Daten"-Disziplin wie der Rest des Projekts).
#
# Braucht KEINEN MT5-Zugriff (liest nur SQLite-Dateien) - kann deutlich
# oefter laufen als der Live-Bot selbst braucht, z.B. stuendlich.
#
# Noch NICHT als Windows-Task-Scheduler-Task eingerichtet (User-Entscheidung
# offen, ob/wie oft).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "gold_asb_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== Gold-ASB-Scan-Task gestartet ==="

try {
    $out = & python scripts\collect_gold_asb_daily_log.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Collector-Fehler: $_"
}

& git add gold_asb_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "Gold ASB Scan: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== Gold-ASB-Scan-Task beendet ==="
