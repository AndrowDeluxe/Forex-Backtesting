# Analog zu scripts\gold_asb_scan_task.ps1: fuehrt den CTNL-Edge-FK-Paper-Bot
# aus (gold_smc_htf_ltf/paper_bot.py), committet+pusht NUR gold_ctnl_edge_logs\,
# komplett unattended.
#
# Frequenz: alle 5 Minuten (matcht Continuations M5-Bar-Groesse - siehe
# knowledge/areas/mt5-bot-deployment.md Punkt 5: "Scheduled-Task-Trigger-
# Frequenz muss zur Bar-Groesse der Strategie passen"). Stuendlicher
# Telegram-Status/Log ist intern in paper_bot.py gegated (last_heartbeat_hour),
# nicht ueber die Task-Frequenz - der Scan selbst muss oefter laufen, um
# Trade-Entries/-Exits zeitnah zu erkennen und zu meldigen.
#
# Noch NICHT als Windows-Task-Scheduler-Task eingerichtet.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "gold_ctnl_edge_logs"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== CTNL-Edge-FK-Paper-Scan gestartet ==="

try {
    $out = & python -m gold_smc_htf_ltf.paper_bot 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Bot-Fehler: $_"
}

& git add gold_ctnl_edge_logs\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    & git commit -m "CTNL Edge FK Paper Scan: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber Streamlit Cloud zeigt ihn NICHT bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== CTNL-Edge-FK-Paper-Scan beendet ==="
