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

Set-Location $repo
try {
    $output = $prompt | & $claudeExe -p --allowedTools "Bash Read Write Edit Glob Grep" --output-format text 2>&1
    $output | ForEach-Object { Log $_ }
} catch {
    Log "FEHLER beim Claude-Aufruf: $_"
}

Log "=== Weekly-Report-Task beendet ==="
