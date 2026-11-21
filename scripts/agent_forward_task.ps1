# Windows Task Scheduler: TradingAgents-Forward (Multi-Agenten-Team ueber das Claude-Abo), seit 21.11.2026.
#   Task "Forex-TradingAgents-Forward": Mo-Fr 22:15 (nach US-Schluss 22:00 MEZ, vor Screener 23:00).
# Das Analyse-Datum MUSS der heutige Tag sein: ein aelteres Datum behandelt TradingAgents als historisch und haelt
# Fundamentaldaten zurueck. Deshalb kein Nachholen am naechsten Morgen (StartWhenAvailable laeuft dann ins Leere,
# der Runner erkennt "US-Schluss heute noch nicht vorbei" bzw. den neuen Tag und schreibt nur die Abrechnung).
# Reiner Analyse-Task: kein Handel, keine Bridge. Laeuft mit der venv C:\Users\andre\TradingAgents\venv.
# Committet NUR fusion_lab/agent_forward/ledger. Muster scripts/screener_task.ps1.

$repo = "C:\Users\andre\Forex-Backtesting"
$py = "C:\Users\andre\TradingAgents\venv\Scripts\python.exe"
. (Join-Path $repo "scripts\lib\git_sync_push.ps1")
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "agent_forward.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8 }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== TradingAgents-Forward gestartet ==="
try {
    $out = & $py -m fusion_lab.agent_forward run 2>&1
    $out | ForEach-Object { Log "$_" }
    Log "Runner Exit-Code $LASTEXITCODE"
    $out = & python -m fusion_lab.dashboard 2>&1
    $out | ForEach-Object { Log "$_" }
    Log "Dashboard Exit-Code $LASTEXITCODE"
} catch {
    Log "Fehler: $_"
}

& git add fusion_lab\agent_forward\ledger\ 2>&1 | ForEach-Object { Log $_ }
& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "TradingAgents-Forward: Ledger $today" 2>&1 | ForEach-Object { Log $_ }
    Sync-AndPush -Log ${function:Log}
}
Log "=== TradingAgents-Forward beendet ==="
