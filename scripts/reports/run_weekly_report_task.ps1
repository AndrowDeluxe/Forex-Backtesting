# Laeuft jeden Sonntagabend (Windows Task Scheduler "Forex-Weekly-Report").
# Ruft Claude Code unbeaufsichtigt (-p, kein Mensch anwesend) mit dem Prompt
# aus weekly_report_prompt.md auf. Findet den claude.exe-Pfad dynamisch unter
# den VSCode-Extensions (die Versionsnummer im Ordnernamen aendert sich bei
# jedem Extension-Update - NICHT hardcoden).
#
# Eng gescopte Tool-Erlaubnis statt vollem --permission-mode bypassPermissions
# (bewusste Nutzer-Entscheidung 2026-08-27): nur Bash/Read/Write/Edit/Glob/Grep
# duerfen ohne Rueckfrage laufen, kein Web-Zugriff, kein Agent-Spawning.

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "scripts\reports"
$logFile = Join-Path $logDir "task_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

Log "=== Weekly-Report-Task gestartet ==="

$extRoot = "$env:USERPROFILE\.vscode\extensions"
$ext = Get-ChildItem $extRoot -Filter "anthropic.claude-code-*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object { [version]($_.Name -replace '^anthropic\.claude-code-(\d+\.\d+\.\d+).*$', '$1') } -Descending |
    Select-Object -First 1
if (-not $ext) {
    Log "FEHLER: keine anthropic.claude-code-Extension unter $extRoot gefunden - Abbruch."
    exit 1
}
$claudeExe = Join-Path $ext.FullName "resources\native-binary\claude.exe"
if (-not (Test-Path $claudeExe)) {
    Log "FEHLER: claude.exe nicht gefunden unter $claudeExe - Abbruch."
    exit 1
}
Log "Nutze Claude Code: $claudeExe"

$weeklyPromptPath = Join-Path $repo "scripts\reports\weekly_report_prompt.md"
$prompt = Get-Content $weeklyPromptPath -Raw

# Letzter Sonntag vor Monatswechsel? Dann Monats-Prompt anhaengen (siehe
# weekly_report_prompt.md, letzter Abschnitt - der Report-Lauf selbst
# entscheidet anhand des Datums, ob er zusaetzlich konsolidiert).
$today = Get-Date
$nextWeek = $today.AddDays(7)
if ($nextWeek.Month -ne $today.Month) {
    Log "Heute ist der letzte Sonntag vor Monatswechsel - haenge Monats-Report-Prompt an."
    $monthlyPromptPath = Join-Path $repo "scripts\reports\monthly_report_prompt.md"
    $prompt += "`n`n---`n`n" + (Get-Content $monthlyPromptPath -Raw)
}

# Merkzeitpunkt fuer die Vollstaendigkeitspruefung unten -- alles, was dieser
# Lauf erzeugt, muss juenger sein als das hier.
$runStart = Get-Date

Set-Location $repo
try {
    $output = $prompt | & $claudeExe -p --allowedTools "Bash Read Write Edit Glob Grep" --output-format text 2>&1
    $output | ForEach-Object { Log $_ }
} catch {
    Log "FEHLER beim Claude-Aufruf: $_"
}

# Vollstaendigkeitspruefung (2026-09-15). Anlass: der Nachhol-Lauf vom 09-14
# lief nach 12 Minuten ins Claude-Session-Limit -- direkt NACH dem Checkup-HTML,
# aber VOR PDF-Rendering, Telegram-Versand und Commit. Der Task meldete
# trotzdem Erfolg (LastTaskResult 0), weil dieses Skript den Ausgang des
# claude.exe-Laufs nie ausgewertet hat: ein halb fertiger Lauf sah exakt aus
# wie ein gelungener. Dasselbe war eine Woche vorher schon passiert (09-13,
# dort das 1-Stunden-Zeitlimit) und faellt sonst nur auf, wenn jemand das
# fehlende PDF bemerkt.
#
# Das PDF ist der letzte Schritt vor dem Versand und damit der beste einzelne
# Indikator fuer "durchgelaufen". Bewusst ueber den Zeitstempel statt ueber den
# erwarteten Dateinamen: welche Kalenderwoche der Lauf abdeckt, entscheidet der
# Prompt, nicht dieses Skript.
$reportDir = "C:\Users\andre\Documents\Trading Reports"
$freshPdf = Get-ChildItem $reportDir -Filter "*.pdf" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $runStart } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($freshPdf) {
    Log "Vollstaendigkeitspruefung OK: $($freshPdf.Name) ($('{0:N0}' -f $freshPdf.Length) Bytes)"
    Log "=== Weekly-Report-Task beendet ==="
} else {
    Log "FEHLER: Lauf unvollstaendig -- kein neues PDF in '$reportDir' seit $($runStart.ToString('HH:mm:ss'))."
    Log "Haeufigste Ursachen: Claude-Session-/Wochenlimit erreicht, oder Zeitlimit des Tasks."
    # Telegram-Warnung, damit ein stiller Teilabbruch nicht erst beim naechsten
    # Blick in den Report-Ordner auffaellt. Darf den Task nicht zum Absturz bringen.
    try {
        $warnScript = Join-Path $logDir "_task_incomplete_warn.py"
        $freshPdfNote = "Weekly Checkup: Lauf unvollstaendig abgebrochen - kein PDF erzeugt. Siehe scripts/reports/task_run.log."
        Set-Content -Path $warnScript -Encoding UTF8 -Value @"
import sys
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\scripts\reports")
from telegram_notify import send_telegram_message, SIGNATURE
send_telegram_message(SIGNATURE + "\n\n" + sys.argv[1])
"@
        & python $warnScript $freshPdfNote 2>&1 | ForEach-Object { Log $_ }
    } catch {
        Log "Telegram-Warnung fehlgeschlagen: $_"
    }
    Log "=== Weekly-Report-Task beendet (UNVOLLSTAENDIG) ==="
    # Exitcode != 0, damit der Task Scheduler den Lauf als fehlgeschlagen
    # erkennt und die eingerichtete Wiederholung (RestartCount/RestartInterval)
    # greift -- bei einem Session-Limit ist ein spaeterer Versuch genau das
    # Richtige.
    exit 1
}
