# Windows Task Scheduler wrapper fuer den CTNL-Edge-FK-Paper-Bot
# (gold_smc_htf_ltf/paper_bot.py) -- gleiches Muster wie scripts/
# cls_practical_scan_task.ps1. Eingerichtet 2026-08-26: der Bot hatte
# bisher KEINEN eigenen Scheduled Task (nur manuell gestartet), letzter
# Heartbeat vor Einrichtung dieses Tasks war 2026-08-20 -- daher blieben
# Telegram-Alerts seither aus, obwohl die Strategie selbst weiterlief
# (bestaetigt ueber die separate, echte CTNL-Edge-MT5-Bridge, die planmaessig
# lief). Dieser Task betrifft NUR den Paper-Forward-Test in diesem Repo,
# nicht die echte Bridge (C:\Users\andre\CTNL-Edge-MT5-Bridge, eigener,
# bereits laufender Scheduled Task "CTNL-Edge-MT5-Bridge").

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
Log "=== CTNL-Edge-FK-Paper-Task gestartet ==="

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
    & git commit -m "CTNL Edge FK-Paper: Snapshot $ts" 2>&1 | ForEach-Object { Log $_ }
    & git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) - Commit liegt lokal vor, aber nicht auf GitHub bis zum naechsten erfolgreichen Push."
    } else {
        Log "Commit + Push erfolgreich."
    }
}

Log "=== CTNL-Edge-FK-Paper-Task beendet ==="
