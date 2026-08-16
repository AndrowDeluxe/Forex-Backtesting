"""Sammelt einen taeglichen Snapshot-Log-Eintrag fuer den BTC-EMA9/21-
Forward-Test (2026-08-16) - PAPIER-Konto, keine echten Orders. Gleiches
"collector laeuft lokal, Seite liest nur committete Daten"-Muster wie
scripts/collect_cls_practical_daily_log.py/collect_ou_modell_daily_log.py.

Anders als bei cls_practical (zustandslos pro Tag) haelt diese Strategie
Positionen ueber Tage/Wochen - btc_ema_cross.live_scan.scan_today() liest
und schreibt den persistenten Zustand in btc_ema_cross_logs/paper_state.json
selbst; dieser Collector haengt nur die heutige Zeile an
btc_ema_cross_logs/daily_log.csv an (ersetzt eine bereits vorhandene Zeile
fuer denselben Tag, keine Duplikate bei mehrfachem Lauf am selben Tag)."""

import csv
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from btc_ema_cross.live_scan import scan_today

OUT_DIR = REPO_DIR / "btc_ema_cross_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"

FIELDS = [
    "date", "yesterday_close", "ema9", "ema21", "above", "go_long_signal",
    "go_flat_signal", "action", "in_position", "equity_mark_to_market", "status",
]


def main() -> None:
    row, _state = scan_today()
    print("BTC-EMA9/21 Tages-Scan (PAPIER, keine echten Orders):")
    for k, v in row.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")

    OUT_DIR.mkdir(exist_ok=True)
    existing_rows = []
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as f:
            existing_rows = [r for r in csv.DictReader(f) if r["date"] != row["date"]]

    full_row = {field: row.get(field, "") for field in FIELDS}
    existing_rows.append(full_row)
    existing_rows.sort(key=lambda r: r["date"])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing_rows)

    print(f"\nGespeichert: {OUT_CSV}")


if __name__ == "__main__":
    main()
