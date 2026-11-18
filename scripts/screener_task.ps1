# Windows Task Scheduler: taeglicher Aktien- bzw. Krypto-Screener + Dashboard (Dachprojekt, 15.11.2026).
#   -File screener_task.ps1 aktien   (Mo-Fr 23:00, nach US-Schluss)
#   -File screener_task.ps1 krypto   (taeglich 07:45, nach den Makro-Daten 07:30)
#   -File screener_task.ps1 rohstoffe (Mo-Fr 23:15, Kern-10-Rohstoffe, seit 18.11.2026)
# Reiner Analyse-Task: kein Handel, keine Bridge. Claude-Einordnung ueber claude.exe -p (Abo).
# Committet NUR Ledger + Archiv (fusion_lab/screener/ledger, archive) -- Protokoll, wann was empfohlen wurde
# (Nutzerwunsch 15.11.2026). Muster scripts/c2_forward_task.ps1.
param([Parameter(Mandatory = $true)][ValidateSet("aktien", "krypto", "rohstoffe")][string]$Art)

$repo = "C:\Users\andre\Forex-Backtesting"
. (Join-Path $repo "scripts\lib\git_sync_push.ps1")
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "screener_$Art.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8 }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== Screener $Art gestartet ==="
try {
    $out = & python -m fusion_lab.screener $Art --telegram --notion 2>&1
    $out | ForEach-Object { Log "$_" }
    Log "Screener Exit-Code $LASTEXITCODE"
    $out = & python -m fusion_lab.dashboard 2>&1
    $out | ForEach-Object { Log "$_" }
    Log "Dashboard Exit-Code $LASTEXITCODE"
} catch {
    Log "Fehler: $_"
}

& git add fusion_lab\screener\ledger\ fusion_lab\screener\archive\ 2>&1 | ForEach-Object { Log $_ }
& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine Aenderungen - kein Commit noetig."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "Screener ${Art}: Ledger + Archiv $today" 2>&1 | ForEach-Object { Log $_ }
    Sync-AndPush -Log ${function:Log}
}
Log "=== Screener $Art beendet ==="
