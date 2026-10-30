# Windows Task Scheduler wrapper fuer den taeglichen Telegram-Import der Gruppe
# "SMH Daily Update" (fusion_lab/ingest/telegram.py, Edge Card Copy Trading).
# Reiner Lese-Task: kein Handel, keine Bridge, kein git commit. Inkrementell,
# laedt nur Nachrichten nach der zuletzt gelesenen ID, ohne Videos. Seit 28.10.2026
# zusaetzlich Forward-Ledger Copy Trading Stufe 2 (fusion_lab/copy_trading/stage2.py).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "fusion_lab\data\logs"
$logFile = Join-Path $logDir "telegram_smh_daily_import.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
Log "=== Telegram-Import SMH Daily Update gestartet ==="

function Step($name, [string[]]$pyArgs) {
    try {
        $out = & python -X utf8 @pyArgs 2>&1
        $out | ForEach-Object { Log "  [$name] $_" }
        if ($LASTEXITCODE -ne 0) { Log "  [$name] Exit-Code $LASTEXITCODE" }
    } catch {
        Log "  [$name] Fehler: $_"
    }
}

Step "Import" @("-m", "fusion_lab.ingest.telegram", "--chat", "-1002552394198", "--skip-video")

# Forward-Test Stufe 2 (Nutzerentscheid 28.10.2026): neue Chartbilder und Anweisungen per
# Claude-Abo auslesen, dann A2 nackt / fest / alle fortschreiben. Nur lesen und rechnen,
# keine Orders. Inkrementell: ein Abbruch (z. B. Abo-Limit) wird am naechsten Abend nachgeholt.
Step "Bilder" @("-m", "fusion_lab.copy_trading.extract", "--since", "2026-10-17")
Step "Anweisungen" @("-m", "fusion_lab.copy_trading.instructions")
Step "Stufe2" @("-m", "fusion_lab.copy_trading.stage2", "--forward")

Log "=== Telegram-Import SMH Daily Update beendet ==="
