# Runs daily via Windows Task Scheduler ("C2-Forward-Log", Di-Sa 03:30) - Forward-Test der
# Daily-Edge C2 + Zins-Momentum + Regime-Matrix (Lock htf_daily_trade_c2_filter, eingefroren
# aea4189b). NUR Log + Telegram, keine Orders (Nutzerentscheid 2026-11-11).
# Rechnet htf_daily_trade/forward/c2_forward_ledger.csv neu, meldet Aenderungen per Telegram
# (samstags mit Wochenbericht) und committet das Ledger. Mirrors daily_orb_forward_test_task.ps1.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "htf_daily_trade\forward"
$logFile = Join-Path $logDir "task_run.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
. (Join-Path $repo "scripts\lib\git_sync_push.ps1")
Log "=== Task gestartet ==="
$env:PYTHONIOENCODING = "utf-8"

$args_py = @("-m", "htf_daily_trade.c2_forward")
if ((Get-Date).DayOfWeek -eq "Saturday") { $args_py += "--wochenbericht" }
try {
    $out = & python @args_py 2>&1
    $out | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log "Scanner-Exitcode $LASTEXITCODE" }
} catch {
    Log "Scanner-Fehler: $_"
}

& git add htf_daily_trade\forward\ 2>&1 | ForEach-Object { Log $_ }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "C2-Forward: Ledger $today" 2>&1 | ForEach-Object { Log $_ }
    Sync-AndPush -Log ${function:Log}
}

Log "=== Task beendet ==="
