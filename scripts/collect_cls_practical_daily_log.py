"""Sammelt einen taeglichen Snapshot-Log-Eintrag fuer den CLS-practical-
Forward-Test (2026-08-13) -- noch KEIN eigener Bot, nur Signal-Tracking
("wie haette die Strategie heute entschieden") als Vorstufe, bevor ein
echter Live-/Paper-Bot gebaut wird (naechster Schritt, User-Ankuendigung).

Gleiches "collector laeuft lokal, Seite liest nur committete Daten"-Muster
wie scripts/collect_ou_modell_daily_log.py/collect_orb_forward_test_log.py --
cls_practical_logs/daily_log.csv wird bei jedem Lauf um die heutige Zeile
ergaenzt (ersetzt eine bereits vorhandene Zeile fuer denselben Tag, keine
Duplikate bei mehrfachem taeglichem Lauf).

Vorgesehen fuer einen taeglichen/stuendlichen Windows-Task-Scheduler-Lauf
waehrend des Entry-Fensters (09:30-12:00 Berlin), analog zum bestehenden
OU-Modell-Scanner-Task -- der Task selbst ist hier noch NICHT eingerichtet,
nur das Skript."""

import csv
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from cls_practical.live_scan import scan_today
OUT_DIR = REPO_DIR / "cls_practical_logs"
OUT_CSV = OUT_DIR / "daily_log.csv"

FIELDS = [
    "date", "break_direction", "holds_0915", "cross_confirmed", "rate_risk_multiplier",
    "triggered", "setup", "direction", "entry_time", "entry_price", "sl", "tp", "status",
]


def main() -> None:
    row = scan_today()
    print("CLS-practical Tages-Scan:")
    for k, v in row.items():
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
