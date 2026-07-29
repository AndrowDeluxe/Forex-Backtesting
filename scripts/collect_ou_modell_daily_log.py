"""Collects one end-of-day summary row for the OU-Modell live trading bot
(C:\\Users\\andre\\OU-Modell-MT5-Bridge, a separate local project - not part
of this repo) and appends it to ou_modell_logs/daily_log.csv here, plus a
copy of the day's raw run-logs to ou_modell_logs/raw/<date>.log.

Why this lives here rather than in the bot's own folder: the bot's local
files (logs/, state.sqlite3, the live MT5 terminal) aren't reachable from
Streamlit Community Cloud. Committing this script's output to the repo is
what lets app_pages/ou_modell.py show real history both locally and on
the deployed dashboard, the same "collect locally, commit, cloud page
reads only committed data" pattern already used for the backtest data
caches (except that data there is regenerable cache and gitignored - this
is unique data and must be tracked).

Read-only against MT5 - never places, modifies, or closes an order.

Intended to run once per day, after the bot's last scheduled scan
(21:30 local) - e.g. via Windows Task Scheduler, same mechanism the bot
itself already uses for its own three daily scans. Safe to re-run for the
same day (the CSV write replaces that day's row instead of duplicating).
"""

import csv
import re
import sqlite3
from datetime import date
from pathlib import Path

BOT_DIR = Path(r"C:\Users\andre\OU-Modell-MT5-Bridge")
BOT_LOG_DIR = BOT_DIR / "logs"
BOT_STATE_DB = BOT_DIR / "state.sqlite3"

REPO_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_DIR / "ou_modell_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"
RAW_DIR = OUT_DIR / "raw"

# Mirrors config.py in the bot's own folder - kept as plain constants here
# rather than importing across repos, since this script only ever needs
# to identify/verify the account, not run the bot itself.
MT5_TERMINAL_PATH = r"C:\Program Files\TTP MT5 Terminal\terminal64.exe"
MT5_LOGIN = 504069845

FIELDS = [
    "date", "signals_scanned", "orders_sent", "orders_skipped", "orders_error",
    "symbols_sent", "baseline_equity", "current_equity", "floating_pnl",
    "daily_pnl_pct", "open_positions", "drawdown_halted", "connection_error",
]


def _todays_logs(today: str) -> list[Path]:
    return sorted(BOT_LOG_DIR.glob(f"run_{today.replace('-', '')}_*.log"))


def _parse_logs(paths: list[Path]) -> dict:
    scanned = sent = skipped = errored = 0
    symbols_sent: list[str] = []
    drawdown_halted = False
    raw_text_parts = []

    for p in paths:
        text = p.read_text(encoding="utf-8")
        raw_text_parts.append(f"===== {p.name} =====\n{text}")
        for m in re.finditer(r"(\d+) Signal\(e\) gescannt\.", text):
            scanned += int(m.group(1))
        for m in re.finditer(r"Ergebnis: \{'status': '(\w+)'.*?'symbol': '([^']+)'", text):
            status, symbol = m.group(1), m.group(2)
            if status == "sent":
                sent += 1
                symbols_sent.append(symbol)
            elif status == "skipped":
                skipped += 1
            elif status == "error":
                errored += 1
        if "Tages-Drawdown-Limit erreicht" in text:
            drawdown_halted = True

    return dict(
        scanned=scanned, sent=sent, skipped=skipped, errored=errored,
        symbols_sent=symbols_sent, drawdown_halted=drawdown_halted,
        raw_text="\n\n".join(raw_text_parts),
    )


def _baseline_equity(today: str) -> float | None:
    if not BOT_STATE_DB.exists():
        return None
    conn = sqlite3.connect(BOT_STATE_DB)
    try:
        row = conn.execute(
            "SELECT baseline_equity FROM daily_baseline WHERE trade_date=?", (today,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _mt5_snapshot() -> dict:
    """Best-effort live read via MT5 - never fatal, since this script must
    still produce a (partial) row from the logs/state DB alone if the
    terminal isn't reachable when it happens to run."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": "MetaTrader5 package not installed"}

    if not mt5.initialize(path=MT5_TERMINAL_PATH):
        return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"mt5.initialize failed: {mt5.last_error()}"}

    try:
        account = mt5.account_info()
        if account is None:
            return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"account_info failed: {mt5.last_error()}"}
        if account.login != MT5_LOGIN:
            return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"connected to account {account.login}, expected {MT5_LOGIN}"}

        positions = mt5.positions_get() or []
        floating_pnl = sum(p.profit for p in positions)
        return {
            "current_equity": account.equity,
            "floating_pnl": floating_pnl,
            "open_positions": "; ".join(f"{p.symbol}({p.profit:+.2f})" for p in positions),
            "connection_error": None,
        }
    finally:
        mt5.shutdown()


def collect(today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    log_paths = _todays_logs(today)
    parsed = _parse_logs(log_paths)
    baseline = _baseline_equity(today)
    snap = _mt5_snapshot()

    current_equity = snap["current_equity"]
    daily_pnl_pct = None
    if baseline and current_equity is not None and baseline > 0:
        daily_pnl_pct = (current_equity - baseline) / baseline

    row = {
        "date": today,
        "signals_scanned": parsed["scanned"],
        "orders_sent": parsed["sent"],
        "orders_skipped": parsed["skipped"],
        "orders_error": parsed["errored"],
        "symbols_sent": ";".join(parsed["symbols_sent"]),
        "baseline_equity": baseline,
        "current_equity": current_equity,
        "floating_pnl": snap["floating_pnl"],
        "daily_pnl_pct": daily_pnl_pct,
        "open_positions": snap["open_positions"],
        "drawdown_halted": parsed["drawdown_halted"],
        "connection_error": snap["connection_error"],
    }

    OUT_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)

    existing_rows = []
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as f:
            existing_rows = [r for r in csv.DictReader(f) if r["date"] != today]
    existing_rows.append(row)
    existing_rows.sort(key=lambda r: r["date"])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing_rows)

    if parsed["raw_text"]:
        (RAW_DIR / f"{today}.log").write_text(parsed["raw_text"], encoding="utf-8")

    return row


if __name__ == "__main__":
    result = collect()
    print("OU-Modell Tages-Log erfasst:")
    for k, v in result.items():
        print(f"  {k}: {v}")
