# Windows Task Scheduler wrapper fuer den Dashboard-Telegram-Digest
# (scripts/reports/dashboard_digest.py). Laeuft jeden Morgen 8:00 (Nutzer-
# wunsch 2026-09-06) und schickt die offenen Punkte aus knowledge/DASHBOARD.md
# per Telegram (gleiche Quelle/Bot wie der Weekly-Report).

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "scripts\reports"
$logFile = Join-Path $logDir "dashboard_digest_task.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Log "=== Dashboard-Telegram-Digest gestartet ==="

Set-Location (Join-Path $repo "scripts\reports")
try {
    # Ohne das hier interpretiert PowerShell die UTF-8-Ausgabe des
    # Python-Prozesses mit der Konsolen-Codepage (cp1252/OEM) -- Umlaute/
    # Emojis im Log werden dadurch zu Mojibake. Betrifft nur das Logfile,
    # nicht die per requests.post() direkt verschickte Telegram-Nachricht.
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $out = & python dashboard_digest.py 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "FEHLER: $_"
}

Log "=== Dashboard-Telegram-Digest beendet ==="
