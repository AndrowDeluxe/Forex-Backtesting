# Runs via Windows Task Scheduler ("Signal-Hub-Scan", alle 10 Min.) - Signal-Hub Stufe 1 (Plan 2026-11-19):
# prueft neue abgeschlossene H4-Kerzen (9 Maerkte), schickt Alarme mit Chart + Ja/Nein-Knoepfen per Telegram.
# NUR Paper/Journal, keine Orders, kein echtes Geld. Commit des Journals hoechstens stuendlich (Minute < 10).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "signal_hub\state"
$logFile = Join-Path $logDir "scan_task.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
try {
    $out = & python -m signal_hub scan 2>&1
    $out | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log "Scan-Exitcode $LASTEXITCODE" }
} catch {
    Log "Scan-Fehler: $_"
}

if ((Get-Date).Minute -lt 10) {
    . (Join-Path $repo "scripts\lib\git_sync_push.ps1")
    & git add signal_hub\journal\ signal_hub\out\ 2>&1 | ForEach-Object { Log $_ }
    & git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $today = Get-Date -Format "yyyy-MM-dd HH:mm"
        & git commit -m "Signal-Hub: Journal $today" 2>&1 | ForEach-Object { Log $_ }
        Sync-AndPush -Log ${function:Log}
    }
}
