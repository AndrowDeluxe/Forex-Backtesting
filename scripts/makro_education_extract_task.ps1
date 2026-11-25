# Windows Task Scheduler wrapper: OneNote-Makro-Education gedrosselt auslesen (lokaler Claude Code, Abo).
# Reiner Lese-Task: kein Handel, keine Bridge, kein git commit.
# Seit 25.11.2026 (Nutzerentscheid): stuendlich 22-06 Uhr je 3 Seiten, damit tagsueber Abo frei bleibt.
# Vorrangseiten (CPI/NFP) zuerst; bei Abo-Grenze bricht das Skript ab und macht naechste Stunde weiter.
# Sobald alle Seiten fertig sind, laeuft der Task leer durch (0 Seiten) und kann deaktiviert werden.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "makro_education_extract.log"

function Log($msg) {
    Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
$code = 1
Log "=== Makro-Education-Auslesen gestartet ==="
try {
    $out = & python -m fusion_lab.inventory.makro_education_extract --all --limit 3 2>&1
    $code = $LASTEXITCODE
    $out | ForEach-Object { Log "$_" }
    Log "Exit-Code $code"
} catch {
    Log "Fehler: $_"
}
Log "=== Makro-Education-Auslesen beendet ==="
exit $code
