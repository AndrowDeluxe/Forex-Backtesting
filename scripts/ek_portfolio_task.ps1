# Windows Task Scheduler wrapper fuer den EK-Portfolio-Paper-Bot
# (ek_portfolio/paper_bot.py) -- gleiches Muster wie scripts/
# fk_instant_funding_task.ps1: lokalen Scan ausfuehren, dessen eigenen
# Output (State + Heartbeat) committen+pushen, komplett unattended.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "ek_portfolio_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== EK-Portfolio-Task gestartet ==="

try {
    $out = & python -m ek_portfolio.paper_bot 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Bot-Fehler: $_"
}

& git add ek_portfolio_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "EK Portfolio Bot: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber nicht auf GitHub bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== EK-Portfolio-Task beendet ==="
