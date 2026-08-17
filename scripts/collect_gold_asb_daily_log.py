"""Sammelt einen Snapshot-Log fuer den Gold-Asian-Range-Breakout-Bot
(2026-08-17), analog zu scripts/collect_cls_practical_daily_log.py -- gleiches
"Collector laeuft lokal, Seite liest nur committete Daten"-Muster, damit
app_pages/gold_asb_live_log.py auch ohne lokalen MT5-Zugriff (z.B. auf
Streamlit Cloud) aktuell bleibt.

Anders als bei CLS Practical wird die Signal-Logik hier NICHT ein zweites Mal
reimplementiert (Gold ASB hat fuenf produktiv validierte Live-Filter -- ADX,
Trend-Bias, Silber-Alignment, Liquiditaet, Fuellverzoegerung -- ein zweiter,
unabhaengiger Nachbau waere ein echtes Fehlerrisiko fuer ein Konto mit realem
Pruef-Kapital, siehe C:\\Users\\andre\\GoldASB-MT5-Bridge\\config.py). Stattdessen
liest dieser Collector direkt den SQLite-State, den der laufende Bot selbst
bei jedem 15-Minuten-Lauf schreibt (windows-Tabelle in
GoldASB-MT5-Bridge/state/<state_id>.sqlite3) -- das ist die tatsaechliche
Wahrheit dessen, was der Bot entschieden hat, nicht eine zweite Meinung
darueber.

Entry/SL werden aus range_high/range_low + config.STOP_FRAC nachgerechnet
(reine Arithmetik, keine Filterlogik) fuer die Seite, die tatsaechlich
scharfgeschaltet wurde (buy_ticket/sell_ticket gesetzt). Kein Take-Profit --
die Strategie nutzt bewusst nur einen Zeit-Exit (siehe GoldASB-MT5-Bridge/
config.py-Docstring)."""

import csv
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REPO_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_DIR / "gold_asb_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"

GOLD_ASB_BRIDGE_DIR = Path(r"C:\Users\andre\GoldASB-MT5-Bridge")

FIELDS = [
    "window_end", "date", "range_high", "range_low", "adx_at_close",
    "armed", "direction", "entry_price", "sl", "buy_ticket", "sell_ticket", "status",
]

_SKIP_LABELS = {
    "adx_filter": "ADX-Regimefilter",
    "trend_silver_conflict": "Trend/Silber uneinig",
    "liquidity_filter": "Liquiditaetsfilter",
    "insufficient_daily_history": "zu wenig Historie",
    "stale_window_price_already_moved": "Fenster bereits ueberlaufen",
    "no_tick": "kein Kurs",
    "delay_filter_expired": "Fuellverzoegerung - storniert",
}


def _rows_for_account(state_db_path: Path, stop_frac: float, limit: int = 90) -> list[dict]:
    if not state_db_path.exists():
        return []

    conn = sqlite3.connect(str(state_db_path))
    try:
        cur = conn.execute(
            "SELECT window_end, range_high, range_low, adx_at_close, armed, "
            "skipped_reason, buy_ticket, sell_ticket FROM windows "
            "ORDER BY window_end DESC LIMIT ?",
            (limit,),
        )
        raw_rows = cur.fetchall()
    finally:
        conn.close()

    rows = []
    for window_end, range_high, range_low, adx_at_close, armed, skipped_reason, buy_ticket, sell_ticket in raw_rows:
        rng = range_high - range_low
        direction = "long" if buy_ticket is not None else ("short" if sell_ticket is not None else None)

        entry_price = sl = None
        if direction == "long":
            entry_price = range_high
            sl = range_high - stop_frac * rng
        elif direction == "short":
            entry_price = range_low
            sl = range_low + stop_frac * rng

        if armed:
            status = f"Setup platziert ({direction})"
        elif skipped_reason:
            status = _SKIP_LABELS.get(skipped_reason, skipped_reason)
        else:
            status = "unbekannt"

        rows.append({
            "window_end": window_end,
            "date": pd.Timestamp(window_end).date().isoformat(),
            "range_high": range_high,
            "range_low": range_low,
            "adx_at_close": round(adx_at_close, 2),
            "armed": bool(armed),
            "direction": direction or "",
            "entry_price": round(entry_price, 2) if entry_price is not None else "",
            "sl": round(sl, 2) if sl is not None else "",
            "buy_ticket": buy_ticket or "",
            "sell_ticket": sell_ticket or "",
            "status": status,
        })
    return rows


def main() -> None:
    sys.path.insert(0, str(GOLD_ASB_BRIDGE_DIR))
    from config import ACCOUNTS, STOP_FRAC  # noqa: E402

    all_rows: list[dict] = []
    for account in ACCOUNTS:
        state_db_path = GOLD_ASB_BRIDGE_DIR / account.state_db_path
        account_rows = _rows_for_account(state_db_path, STOP_FRAC)
        print(f"{account.name}: {len(account_rows)} Fenster gelesen ({state_db_path}).")
        all_rows.extend(account_rows)

    if not all_rows:
        print("Keine Fenster gefunden -- Bot noch nicht gelaufen oder State-DB fehlt.")
        return

    OUT_DIR.mkdir(exist_ok=True)
    existing_rows = []
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as f:
            seen_keys = {r["window_end"] for r in all_rows}
            existing_rows = [r for r in csv.DictReader(f) if r["window_end"] not in seen_keys]

    merged = existing_rows + all_rows
    merged.sort(key=lambda r: r["window_end"])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged)

    latest = all_rows[0]  # sorted DESC from the DB query
    print(f"\nAktuellstes Fenster: {latest['window_end']} -- {latest['status']}")
    print(f"Gespeichert: {OUT_CSV}")


if __name__ == "__main__":
    main()
