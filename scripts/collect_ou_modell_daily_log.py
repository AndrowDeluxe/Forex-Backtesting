"""Collects one end-of-day summary row PER ACCOUNT for the OU-Modell live
trading bot (C:\\Users\\andre\\OU-Modell-MT5-Bridge, a separate local project -
not part of this repo) and appends it to ou_modell_logs/daily_log.csv here,
plus a copy of each account's raw run-logs to
ou_modell_logs/raw/<account_id>/<date>.log.

Why this lives here rather than in the bot's own folder: the bot's local
files (logs/, state DBs, the live MT5 terminals) aren't reachable from
Streamlit Community Cloud. Committing this script's output to the repo is
what lets app_pages/ou_modell.py show real history both locally and on
the deployed dashboard, the same "collect locally, commit, cloud page
reads only committed data" pattern already used for the backtest data
caches (except that data there is regenerable cache and gitignored - this
is unique data and must be tracked).

Multi-account since 2026-07-31 (mirrors the bot's own config.ACCOUNTS,
kept as plain constants here rather than importing across repos - this
script only ever needs to identify/read each account, not run the bot
itself). Deliberately holds NO passwords: this repo has a public GitHub
remote (a separate scheduled task commits+pushes ou_modell_logs/ daily),
so unlike the bot's own config.py this file must never contain credentials.
Each account's own MT5 terminal is permanently logged into exactly that
account now (no more runtime account-switching within a terminal, see the
bot's config.py for why), so a bare mt5.initialize(path=...) attaches
without needing a login/password here - same pattern the bot's OWN
connect() used before the multi-account rollout.

Read-only against MT5 - never places, modifies, or closes an order.

Intended to run once per day, after the bot's last scheduled scan (21:35
local, hourly since 15:35) - e.g. via Windows Task Scheduler, same mechanism
the bot itself already uses for its own scans. Safe to re-run for the same
day (the CSV write replaces that day's row per account instead of
duplicating).

Produces one row per account per day, but breaks each individual hourly run
out into the "hourly_breakdown" column (a JSON list, one entry per
run_*.log with that run's time + counts) so app_pages/ou_modell.py can
render a clear per-scan table without needing more than one row per
account per day.
"""

import ast
import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BOT_DIR = Path(r"C:\Users\andre\OU-Modell-MT5-Bridge")

REPO_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_DIR / "ou_modell_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"
RAW_DIR = OUT_DIR / "raw"


@dataclass(frozen=True)
class AccountSpec:
    name: str  # display label, matches the bot's AccountConfig.name
    state_id: str  # matches the bot's AccountConfig.state_id (folder/file naming)
    mt5_terminal_path: str
    mt5_login: int


# Mirrors config.ACCOUNTS in the bot's own folder - see module docstring for
# why this intentionally excludes passwords/servers (not needed for a bare
# read-only attach to an already-dedicated, already-logged-in terminal).
ACCOUNTS = [
    AccountSpec(
        name="Konto 1 (TTP)",
        state_id="konto1_ttp",
        mt5_terminal_path=r"C:\Program Files\TTP MT5 Terminal\terminal64.exe",
        mt5_login=504069845,
    ),
    AccountSpec(
        name="Konto 2 (TTP, Demo)",
        state_id="konto2_ttp",
        mt5_terminal_path=r"C:\Users\andre\MT5-Terminals\TTP MT5 Terminal - Konto2\terminal64.exe",
        mt5_login=504072729,
    ),
    AccountSpec(
        name="Konto 3 (Tickmill)",
        state_id="konto3_tickmill",
        mt5_terminal_path=r"C:\Program Files\Tickmill Europe MT5 Terminal\terminal64.exe",
        mt5_login=55918977,
    ),
]

FIELDS = [
    "date", "account", "signals_scanned", "orders_sent", "orders_skipped", "orders_error",
    "symbols_sent", "baseline_equity", "current_equity", "floating_pnl",
    "daily_pnl_pct", "open_positions", "drawdown_halted", "connection_error",
    "hourly_breakdown",
]

_RUN_FILENAME_RE = re.compile(r"run_(\d{8})_(\d{6})\.log$")


def _todays_logs(account: AccountSpec, today: str) -> list[Path]:
    log_dir = BOT_DIR / "logs" / account.state_id
    return sorted(log_dir.glob(f"run_{today.replace('-', '')}_*.log"))


def _parse_single_run(path: Path, text: str) -> dict:
    """Fasst EINEN stündlichen Scan-Lauf zusammen (ein run_*.log), für die
    stündliche Aufschlüsselung auf der Dashboard-Seite. Nutzt ast.literal_eval
    auf den geloggten Python-Dict-Reprs (robuster als Teil-Feld-Regexe, da die
    Zeilen z.B. bei Pending-Orders ein verschachteltes 'order'-Dict enthalten)."""

    m = _RUN_FILENAME_RE.search(path.name)
    time_label = f"{m.group(2)[:2]}:{m.group(2)[2:4]}" if m else path.name

    scanned = 0
    for sm in re.finditer(r"(\d+) Signal\(e\)(?: gescannt| verfügbar)", text):
        scanned += int(sm.group(1))

    sent = pending_placed = skipped = errored = 0
    sent_symbols: list[str] = []
    pending_symbols: list[str] = []

    for rm in re.finditer(r"Ergebnis: (\{.*\})\s*$", text, re.MULTILINE):
        try:
            result = ast.literal_eval(rm.group(1))
        except (ValueError, SyntaxError):
            continue
        status = result.get("status")
        symbol = (result.get("signal") or {}).get("symbol")
        order_type = (result.get("order") or {}).get("type")

        if status == "sent" or (status == "dry_run" and order_type == "BUY"):
            sent += 1
            if symbol:
                sent_symbols.append(symbol)
        elif status == "pending_placed" or (status == "dry_run" and order_type in ("BUY_LIMIT", "BUY_STOP")):
            pending_placed += 1
            if symbol:
                pending_symbols.append(symbol)
        elif status == "skipped":
            skipped += 1
        elif status == "error":
            errored += 1

    def _count_status(label: str, wanted: set[str]) -> int:
        lm = re.search(rf"{label}: (\[.*\])\s*$", text, re.MULTILINE)
        if not lm:
            return 0
        try:
            entries = ast.literal_eval(lm.group(1))
        except (ValueError, SyntaxError):
            return 0
        return sum(1 for e in entries if e.get("status") in wanted)

    be_moved = _count_status("Break-Even-Management", {"moved", "dry_run"})
    pending_cancelled = _count_status("Pending-Order-Management", {"cancelled", "dry_run"})

    return {
        "time": time_label,
        "signals_scanned": scanned,
        "sent": sent,
        "sent_symbols": sent_symbols,
        "pending_placed": pending_placed,
        "pending_symbols": pending_symbols,
        "skipped": skipped,
        "error": errored,
        "be_moved": be_moved,
        "pending_cancelled": pending_cancelled,
        "drawdown_halted": "Tages-Drawdown-Limit erreicht" in text,
        "scan_failed": "Scan endgültig fehlgeschlagen" in text,
    }


def _parse_logs(paths: list[Path]) -> dict:
    scanned = sent = skipped = errored = 0
    symbols_sent: list[str] = []
    drawdown_halted = False
    raw_text_parts = []
    hourly_breakdown = []

    for p in paths:
        text = p.read_text(encoding="utf-8")
        raw_text_parts.append(f"===== {p.name} =====\n{text}")
        hourly_breakdown.append(_parse_single_run(p, text))
        for m in re.finditer(r"(\d+) Signal\(e\)(?: gescannt| verfügbar)", text):
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
        raw_text="\n\n".join(raw_text_parts), hourly_breakdown=hourly_breakdown,
    )


def _baseline_equity(account: AccountSpec, today: str) -> float | None:
    state_db = BOT_DIR / "state" / f"{account.state_id}.sqlite3"
    if not state_db.exists():
        return None
    conn = sqlite3.connect(state_db)
    try:
        row = conn.execute(
            "SELECT baseline_equity FROM daily_baseline WHERE trade_date=?", (today,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _mt5_snapshot(account: AccountSpec) -> dict:
    """Best-effort live read via MT5 - never fatal, since this script must
    still produce a (partial) row from the logs/state DB alone if a
    terminal isn't reachable when it happens to run. A bare
    mt5.initialize(path=...) with no login/password is enough here: each
    account's terminal is permanently dedicated to that one account since
    the 2026-07-31 multi-account rollout (see the bot's config.py), so this
    just attaches and verifies rather than logging in."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": "MetaTrader5 package not installed"}

    if not mt5.initialize(path=account.mt5_terminal_path):
        return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"mt5.initialize failed: {mt5.last_error()}"}

    try:
        info = mt5.account_info()
        if info is None:
            return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"account_info failed: {mt5.last_error()}"}
        if info.login != account.mt5_login:
            return {"current_equity": None, "floating_pnl": None, "open_positions": None, "connection_error": f"connected to account {info.login}, expected {account.mt5_login}"}

        positions = mt5.positions_get() or []
        floating_pnl = sum(p.profit for p in positions)
        return {
            "current_equity": info.equity,
            "floating_pnl": floating_pnl,
            "open_positions": "; ".join(f"{p.symbol}({p.profit:+.2f})" for p in positions),
            "connection_error": None,
        }
    finally:
        mt5.shutdown()


def _collect_account(account: AccountSpec, today: str) -> dict:
    log_paths = _todays_logs(account, today)
    parsed = _parse_logs(log_paths)
    baseline = _baseline_equity(account, today)
    snap = _mt5_snapshot(account)

    current_equity = snap["current_equity"]
    daily_pnl_pct = None
    if baseline and current_equity is not None and baseline > 0:
        daily_pnl_pct = (current_equity - baseline) / baseline

    row = {
        "date": today,
        "account": account.name,
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
        "hourly_breakdown": json.dumps(parsed["hourly_breakdown"], ensure_ascii=False),
    }

    if parsed["raw_text"]:
        raw_account_dir = RAW_DIR / account.state_id
        raw_account_dir.mkdir(parents=True, exist_ok=True)
        (raw_account_dir / f"{today}.log").write_text(parsed["raw_text"], encoding="utf-8")

    return row


def collect(today: str | None = None) -> list[dict]:
    today = today or date.today().isoformat()
    OUT_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)

    rows = [_collect_account(account, today) for account in ACCOUNTS]

    existing_rows = []
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Vor 2026-07-31 gab es keine "account"-Spalte (Ein-Konto-Ära) -
                # diese Altzeilen gehören alle zu Konto 1, dem einzigen Konto,
                # das es damals gab.
                if not r.get("account"):
                    r["account"] = "Konto 1 (TTP)"
                key = (r["date"], r["account"])
                if key not in {(row["date"], row["account"]) for row in rows}:
                    existing_rows.append(r)

    all_rows = existing_rows + rows
    all_rows.sort(key=lambda r: (r["date"], r["account"]))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    return rows


if __name__ == "__main__":
    results = collect()
    for result in results:
        print(f"OU-Modell Tages-Log erfasst ({result['account']}):")
        for k, v in result.items():
            print(f"  {k}: {v}")
        print()
