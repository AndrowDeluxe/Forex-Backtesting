# Einmaliger Task "Forex-NVDA-Earnings-Analyse" (Di 17.11.2026, 23:45): NVIDIA-Analyse nach den
# Quartalszahlen per Telegram (Nutzerauftrag 15.11.2026). Ruft Claude Code unbeaufsichtigt (-p) mit
# scripts/reports/nvda_followup_prompt.md auf. Web-Zugriff ist hier noetig (Zahlen, News), deshalb
# WebSearch/WebFetch zusaetzlich zu den Werkzeugen des Weekly-Reports. Kein Handel, keine Bridge, kein Commit.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "nvda_followup.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" -Encoding utf8 }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

Log "=== NVDA-Earnings-Analyse gestartet ==="
$extRoot = "$env:USERPROFILE\.vscode\extensions"
$ext = Get-ChildItem $extRoot -Filter "anthropic.claude-code-*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object { [version]($_.Name -replace '^anthropic\.claude-code-(\d+\.\d+\.\d+).*$', '$1') } -Descending |
    Select-Object -First 1
if (-not $ext) { Log "FEHLER: keine Claude-Code-Extension gefunden"; exit 1 }
$claudeExe = Join-Path $ext.FullName "resources\native-binary\claude.exe"
if (-not (Test-Path $claudeExe)) { Log "FEHLER: claude.exe fehlt unter $claudeExe"; exit 1 }

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
$prompt = Get-Content (Join-Path $repo "scripts\reports\nvda_followup_prompt.md") -Raw
try {
    $out = $prompt | & $claudeExe -p --allowedTools "Bash Read Write Edit Glob Grep WebSearch WebFetch" --output-format text 2>&1
    $out | ForEach-Object { Log "$_" }
} catch {
    Log "FEHLER beim Claude-Aufruf: $_"
}

# Sicherheitsnetz: Wurde keine Nachricht geschrieben, wenigstens Bescheid geben.
$msg = Join-Path $repo "fusion_lab\data\screener\nvda_followup_2026-11-17.txt"
if (-not (Test-Path $msg)) {
    $fail = Join-Path $logDir "nvda_followup_fehler.txt"
    "NVIDIA-Analyse nach den Zahlen: Der geplante Lauf ist fehlgeschlagen. Log: fusion_lab\data\logs\nvda_followup.log" |
        Set-Content -Path $fail -Encoding utf8
    & python (Join-Path $repo "scripts\reports\send_telegram_text.py") $fail | ForEach-Object { Log "$_" }
}
Log "=== NVDA-Earnings-Analyse beendet ==="
