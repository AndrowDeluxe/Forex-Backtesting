# Windows Task Scheduler wrapper: Datenschicht des Makro-Agenten abrufen.
# Reiner Daten-Task: kein Handel, keine Bridge, kein git commit.
# Laeuft 07:30 und 00:50: Der Myfxbook-Feed zeigt nur den laufenden Tag (GMT), der
# Nachtlauf sichert die Ist-Werte des Tages, der Morgenlauf den Konsens vor den Prints.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "macro_data.log"

function Log($msg) {
    Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== Makro-Daten gestartet ==="
try {
    $out = & python -m fusion_lab.macro_data 2>&1
    $out | Where-Object { "$_" -notmatch "DUKASCRIPT" } | ForEach-Object { Log "$_" }
    Log "Exit-Code $LASTEXITCODE"
} catch {
    Log "Fehler: $_"
}
Log "=== Makro-Daten beendet ==="
