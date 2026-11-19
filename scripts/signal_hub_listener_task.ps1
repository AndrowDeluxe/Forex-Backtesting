# Runs via Windows Task Scheduler ("Signal-Hub-Listener", alle 2 Min.) - Signal-Hub Stufe 1 (Plan 2026-11-19):
# holt Telegram-Knopfdruecke (Ja/Nein/Spaeter), markiert verfallene Signale, schickt Erinnerungen und rechnet die
# Paper-Positionen nach. Kein git, keine Orders.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "signal_hub\state"
$logFile = Join-Path $logDir "listener_task.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
try {
    $out = & python -m signal_hub listen 2>&1
    if ($out) { $out | ForEach-Object { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $_" } }
} catch {
    Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') Listener-Fehler: $_"
}
