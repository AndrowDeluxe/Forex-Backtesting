"""Collects one end-of-day summary row for the ORB forward test
(C:\\Users\\andre\\ORB-MT5-ForwardTest, a separate local project - not part
of this repo, see MEMORY) and appends it to
orb_forward_test_logs/daily_log.csv here, plus a concatenated copy of the
day's raw run-logs to orb_forward_test_logs/raw/<date>.log.

Same "collect locally, commit, cloud page reads only committed data"
pattern as scripts/collect_ou_modell_daily_log.py, for the same reason:
the forward-test project's logs/state DB/MT5 terminal live outside this
repo and aren't reachable from Streamlit Community Cloud.

Read-only against MT5 - never places, modifies, or closes an order.

Intended to run once per day (e.g. shortly before UTC midnight, or any
time - it aggregates whatever run_*.log files exist for "today" so far).
Safe to re-run for the same day (replaces that day's row instead of
duplicating).
"""

import csv
import re
import sqlite3
from datetime import date
from pathlib import Path

BOT_DIR = Path(r"C:\Users\andre\ORB-MT5-ForwardTest")
BOT_LOG_DIR = BOT_DIR / "logs"
BOT_STATE_DB = BOT_DIR / "state.sqlite3"

REPO_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_DIR / "orb_forward_test_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"
TRADES_CSV = OUT_DIR / "trades.csv"
RAW_DIR = OUT_DIR / "raw"

TRADE_FIELDS = ["trade_date", "symbol", "direction", "entry_price", "stop_price", "mt5_ticket", "executed_at", "dry_run"]

# Mirrors config.py in the forward-test's own folder - kept as a plain
# constant here rather than importing across repos.
MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_LOGIN = 110209087

FIELDS = [
    "date", "runs", "orders_sent", "orders_skipped", "orders_error",
    "session_end_closes", "symbols_traded", "current_equity", "floating_pnl",
    "open_positions", "connection_error",
]


def _todays_logs(today: str) -> list[Path]:
    return sorted(BOT_LOG_DIR.glob(f"run_{today.replace('-', '')}_*.log"))


def _parse_logs(paths: list[Path]) -> dict:
    sent = skipped = errored = closes = 0
    symbols_sent: list[str] = []
    raw_text_parts = []

    for p in paths:
        text = p.read_text(encoding="utf-8")
        raw_text_parts.append(f"===== {p.name} =====\n{text}")
        for m in re.finditer(r": (\{'status': '(\w+)'[^\n]*\})", text):
            status = m.group(2)
            if status in ("sent", "dry_run"):
                sent += 1
                sym_m = re.search(r"'symbol': '([^']+)'", m.group(1))
                if sym_m:
                    symbols_sent.append(sym_m.group(1))
            elif status == "skipped":
                skipped += 1
            elif status == "error":
                errored += 1
        closes += len(re.findall(r"'status': '(?:closed|dry_run_close)'", text))

    return dict(
        runs=len(paths), sent=sent, skipped=skipped, errored=errored, closes=closes,
        symbols_sent=symbols_sent, raw_text="\n\n".join(raw_text_parts),
    )


def _executed_symbols_today(today: str) -> list[str]:
    if not BOT_STATE_DB.exists():
        return []
    conn = sqlite3.connect(BOT_STATE_DB)
    try:
        rows = conn.execute(
            "SELECT symbol FROM executed_signals WHERE trade_date=?", (today,)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def _sync_trades_csv() -> None:
    """Copies the full executed_signals table (every entry ever taken, not
    just today's) into orb_forward_test_logs/trades.csv - the source of
    truth for individual trade entries (symbol/direction/entry/stop),
    which app_pages/orb_forward_test.py plots as markers on a candlestick
    chart. Simpler and more reliable than regex-parsing log text for this,
    since the state DB already has exactly these fields structured."""

    if not BOT_STATE_DB.exists():
        return
    conn = sqlite3.connect(BOT_STATE_DB)
    try:
        rows = conn.execute(
            "SELECT trade_date, symbol, direction, entry_price, stop_price, mt5_ticket, executed_at, dry_run "
            "FROM executed_signals ORDER BY trade_date, symbol"
        ).fetchall()
    finally:
        conn.close()

    with open(TRADES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(TRADE_FIELDS)
        writer.writerows(rows)


def _mt5_snapshot() -> dict:
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
    paths = _todays_logs(today)
    parsed = _parse_logs(paths)
    executed = _executed_symbols_today(today)
    snap = _mt5_snapshot()

    row = {
        "date": today,
        "runs": parsed["runs"],
        "orders_sent": parsed["sent"],
        "orders_skipped": parsed["skipped"],
        "orders_error": parsed["errored"],
        "session_end_closes": parsed["closes"],
        "symbols_traded": ";".join(sorted(set(parsed["symbols_sent"]) | set(executed))),
        "current_equity": snap["current_equity"],
        "floating_pnl": snap["floating_pnl"],
        "open_positions": snap["open_positions"],
        "connection_error": snap["connection_error"],
    }

    OUT_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    _sync_trades_csv()

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
    print("ORB-Forward-Test Tages-Log erfasst:")
    for k, v in result.items():
        print(f"  {k}: {v}")
