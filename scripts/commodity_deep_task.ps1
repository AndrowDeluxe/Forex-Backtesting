# Woechentlicher Task "Forex-Rohstoff-Tiefenanalyse" (So 18:00, seit 18.11.2026): Tiefen-Analyse je
# Kern-10-Rohstoff im Stil der Kupfer-Analyse vom 18.11. (News, Sentiment, Makro, Angebot/Nachfrage, Technik).
# Ruft Claude Code unbeaufsichtigt (-p) je Rohstoff nacheinander auf (Prompt: scripts/reports/commodity_deep.py).
# Web-Zugriff noetig. Kein Handel, keine Bridge. Committet NUR fusion_lab/screener/archive/rohstoffe_tief/.
# Danach Dashboard neu bauen + Telegram-Sammelkurzfassung. Muster: scripts/nvda_followup_task.ps1, screener_task.ps1.

$repo = "C:\Users\andre\Forex-Backtesting"
. (Join-Path $repo "scripts\lib\git_sync_push.ps1")
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "rohstoff_tief.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8 }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

Log "=== Rohstoff-Tiefenanalyse gestartet ==="
$extRoot = "$env:USERPROFILE\.vscode\extensions"
$ext = Get-ChildItem $extRoot -Filter "anthropic.claude-code-*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object { [version]($_.Name -replace '^anthropic\.claude-code-(\d+\.\d+\.\d+).*$', '$1') } -Descending |
    Select-Object -First 1
if (-not $ext) { Log "FEHLER: keine Claude-Code-Extension gefunden"; exit 1 }
$claudeExe = Join-Path $ext.FullName "resources\native-binary\claude.exe"
if (-not (Test-Path $claudeExe)) { Log "FEHLER: claude.exe fehlt unter $claudeExe"; exit 1 }

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
$helper = Join-Path $repo "scripts\reports\commodity_deep.py"
$keys = & python $helper liste
foreach ($k in $keys) {
    $k = $k.Trim()
    if (-not $k) { continue }
    Log "--- $k ---"
    try {
        $prompt = (& python $helper prompt $k) -join "`n"
        $out = $prompt | & $claudeExe -p --allowedTools "Bash Read Write Edit Glob Grep WebSearch WebFetch" --output-format text 2>&1
        $out | Select-Object -Last 5 | ForEach-Object { Log "$_" }
    } catch {
        Log "FEHLER bei ${k}: $_"
    }
}

try {
    & python -m fusion_lab.dashboard 2>&1 | ForEach-Object { Log "$_" }
    $msg = Join-Path $logDir "rohstoff_tief_telegram.txt"
    (& python $helper telegram) -join "`n" | Set-Content -Path $msg -Encoding utf8
    & python (Join-Path $repo "scripts\reports\send_telegram_text.py") $msg | ForEach-Object { Log "$_" }
} catch {
    Log "FEHLER Dashboard/Telegram: $_"
}

& git add fusion_lab\screener\archive\rohstoffe_tief\ 2>&1 | ForEach-Object { Log $_ }
& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "Keine neuen Analysen - kein Commit."
} else {
    $today = Get-Date -Format "yyyy-MM-dd"
    & git commit -m "Rohstoff-Tiefenanalyse $today" 2>&1 | ForEach-Object { Log $_ }
    Sync-AndPush -Log ${function:Log}
}
Log "=== Rohstoff-Tiefenanalyse beendet ==="
