# Windows Task Scheduler wrapper fuer den Challenge-Portfolio-Paper-Bot
# (challenge_portfolio/paper_bot.py) -- gleiches Muster wie scripts/
# fk_instant_funding_task.ps1: lokalen Scan ausfuehren, dessen eigenen
# Output (State + Heartbeat) committen+pushen, komplett unattended.
#
# NICHT in Task Scheduler eingerichtet (Stand 2026-08-27) -- Aktivierung ist
# eine bewusste, separate Nutzer-Entscheidung, gleiches Vorgehen wie beim
# CTNL-FK-Scan-Task (scripts/gold_ctnl_edge_fk_scan_task.ps1).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "challenge_portfolio_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== Challenge-Portfolio-Task gestartet ==="

try {
    $out = & python -m challenge_portfolio.paper_bot 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Bot-Fehler: $_"
}

& git add challenge_portfolio_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "Challenge Portfolio Bot: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber nicht auf GitHub bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== Challenge-Portfolio-Task beendet ==="
