# Windows Task Scheduler wrapper fuer den FK-Instant-Funding-Paper-Bot
# (fk_instant_funding/paper_bot.py) -- gleiches Muster wie scripts/
# cls_practical_scan_task.ps1: lokalen Scan ausfuehren, dessen eigenen
# Output (State + Heartbeat) committen+pushen, komplett unattended.
# Eingerichtet 2026-08-26 auf Anfrage des Users, nachdem der bestehende
# In-Repo-CTNL-Paper-Bot (gold_smc_htf_ltf/paper_bot.py) ohne eigenen
# Scheduled Task seit 2026-08-20 nicht mehr gelaufen war -- derselbe Fehler
# soll diesem neuen Bot nicht passieren.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fk_instant_funding_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== FK-Instant-Funding-Task gestartet ==="

try {
    $out = & python -m fk_instant_funding.paper_bot 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Bot-Fehler: $_"
}

& git add fk_instant_funding_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "FK Instant Funding Bot: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber nicht auf GitHub bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== FK-Instant-Funding-Task beendet ==="
