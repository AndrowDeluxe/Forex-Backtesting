# Windows Task Scheduler wrapper fuer den Data-Lake-Ingestion-Task
# (data_lake/ingest.py) -- drei Kadenzen, siehe data_lake/sources.py-Docstring:
#   -Universe fast   (alle 15 Min., Dukascopy/TradingView-Beine)
#   -Universe fast5  (alle 5 Min., NUR ctnl_continuation/orb's M5/M15-Keys,
#                     siehe DASHBOARD.md 2026-09-02-Entscheidung)
#   -Universe slow   (stuendlich, OU-Modell/yfinance, ~163 Ticker)
# Kein git add/commit/push hier -- der Lake-Inhalt (data_lake_store/) ist
# gitignored, anders als challenge_portfolio_task.ps1's State-Commit-Muster.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("fast", "fast5", "slow")]
    [string]$Universe
)

$repo = "C:\Users\andre\Forex-Backtesting"
$logDir = Join-Path $repo "data_lake_logs"
$logFile = Join-Path $logDir "task_run_$Universe.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $repo
Log "=== Data-Lake-Ingest ($Universe) gestartet ==="

try {
    $out = & python -m data_lake.ingest --universe $Universe 2>&1
    $out | ForEach-Object { Log $_ }
} catch {
    Log "Ingest-Fehler: $_"
}

Log "=== Data-Lake-Ingest ($Universe) beendet ==="
