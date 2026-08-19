"""Sammelt einen taeglichen Snapshot des Cross-Filters (cls_practical.
currency_strength.compute_cross_vote_confirmation) fuer EUR/USD (2026-08-19,
User-Wunsch: "den Cross Asset Filter separiert auf Streamlit als neuen Tab
... visuell sichtbar machen, so dass ich selber taeglich abchecken kann was
passiert"). Gleiches "Collector laeuft lokal, Seite liest nur committete
Daten"-Muster wie scripts/collect_cls_practical_daily_log.py -- der
Cross-Filter braucht dieselbe (relativ schwere) 10-Paare-M15 + EUR/USD-M5-
Datenlast, deshalb NICHT live aus Streamlit Cloud gefetcht.

WICHTIG: der Cross-Filter ist NICHT der aktuell live gehandelte
Cross-Confirmation-Mechanismus (das bleibt strategy.cls_advanced.
compute_cross_confirmation, USD-only, siehe cls_practical/live_scan.py) --
er ist der 2026-08-18/19 als Alternative getestete, gleichgewichtete
Mehrheits-Cross-Vote (siehe cls_practical/currency_strength.py), der beim
EUR/USD-Fenster/Schwellen-Sweep KEINEN klaren Mehrwert gegenueber der
Baseline zeigte (scripts/research_cls_practical_window_threshold_holdtest_sweep.py,
Sweep A) und deshalb NICHT in den Live-Pfad uebernommen wurde. Diese Seite
ist Monitoring/Research, keine Live-Signal-Quelle.

Schreibt/ersetzt bei JEDEM Lauf alle Tage im Trailing-Fenster mit
vollstaendiger Break-Richtung (nicht nur "heute") - macht den allerersten
Lauf sofort nutzbar (History-Backfill fuer die neue Seite) und aktualisiert
nebenbei die letzten Tage erneut, falls sich an den Daten noch etwas
korrigiert hat. "Heute" erscheint automatisch, sobald die Settle-Range
(06:00-09:00 Berlin) fertig ist - vorher taucht das heutige Datum einfach
noch nicht auf, kein Fehler.

Zwei CSVs:
- cls_practical_logs/cross_filter_daily_log.csv: eine Zeile pro Tag
  (Aggregat: confirm_ratio, confirmed, n_confirm/n_total).
- cls_practical_logs/cross_filter_breakdown_log.csv: mehrere Zeilen pro Tag
  (je Referenzpaar: welche Waehrung geprueft, move_pct, vote_agrees).

Vorgesehen fuer denselben taeglichen Windows-Task-Scheduler-Lauf wie
collect_cls_practical_daily_log.py (kann im selben Task-Schritt mitlaufen)."""

import csv
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from cls_practical.currency_strength import compute_cross_vote_confirmation, cross_vote_breakdown
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin
from strategy.cls_advanced import compute_daily_features

TRADED_PAIR = "EURUSD"
REF_BASKET = ["EURGBP", "EURCHF", "EURCAD", "EURAUD", "EURJPY",
              "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
LOOKBACK_DAYS = 60
CHECKPOINT_HOUR = 9.0  # matches engine.py's current hold-test checkpoint default (2026-08-19)
WINDOW = "day_start"
CONFIRM_THRESHOLD = 0.5

OUT_DIR = REPO_DIR / "cls_practical_logs"
DAILY_CSV = OUT_DIR / "cross_filter_daily_log.csv"
BREAKDOWN_CSV = OUT_DIR / "cross_filter_breakdown_log.csv"

DAILY_FIELDS = ["date", "break_direction", "n_confirm", "n_total", "confirm_ratio", "confirmed", "strong_confirmed"]
BREAKDOWN_FIELDS = ["date", "ref_pair", "checked_currency", "move_pct", "vote_agrees"]


def _replace_dates_and_write(path: Path, fields: list[str], new_rows: list[dict]) -> None:
    """Overwrites any existing row(s) sharing a date with `new_rows`, keeps
    everything else, single read+write (not one round-trip per date)."""
    if not new_rows:
        return
    replace_dates = {r["date"] for r in new_rows}
    existing = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            existing = [r for r in csv.DictReader(f) if r["date"] not in replace_dates]
    existing.extend(new_rows)
    existing.sort(key=lambda r: (r["date"], r.get("ref_pair", "")))
    OUT_DIR.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(existing)


def main() -> None:
    today = dt.date.today()
    start = (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = today.isoformat()

    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", start, end, force_refresh=True)
    ref_m15 = {p: fetch_major_m15_berlin(p, start, end, force_refresh=True) for p in REF_BASKET}

    if eurusd_m5.empty:
        print("Keine Daten (Wochenende/Feiertag/Fehler) -- kein Log-Eintrag.")
        return

    daily = compute_daily_features(eurusd_m5, test_hour=CHECKPOINT_HOUR)
    direction = daily["direction"]
    conf = compute_cross_vote_confirmation(
        TRADED_PAIR, direction, ref_m15, checkpoint_hour=CHECKPOINT_HOUR, window=WINDOW, confirm_threshold=CONFIRM_THRESHOLD,
    )
    detail = cross_vote_breakdown(TRADED_PAIR, direction, ref_m15, checkpoint_hour=CHECKPOINT_HOUR, window=WINDOW)

    daily_rows = []
    for day in daily.index:
        d_dir = direction.loc[day]
        if pd.isna(d_dir) or d_dir == 0:
            continue
        c = conf.loc[day] if day in conf.index else None
        has_ratio = c is not None and pd.notna(c["confirm_ratio"])
        daily_rows.append({
            "date": day.isoformat(),
            "break_direction": {1: "long", -1: "short"}.get(d_dir, "n/a"),
            "n_confirm": int(c["n_confirm"]) if c is not None else "",
            "n_total": int(c["n_total"]) if c is not None else "",
            "confirm_ratio": round(float(c["confirm_ratio"]), 4) if has_ratio else "",
            "confirmed": bool(c["confirmed"]) if has_ratio else "",
            "strong_confirmed": bool(c["strong_confirmed"]) if has_ratio else "",
        })

    if not daily_rows:
        print("Keine Tage mit vollstaendiger Break-Richtung im Fenster -- kein Log-Eintrag.")
        return

    latest = daily_rows[-1]
    print(f"Cross-Filter Scan: {len(daily_rows)} Tag(e) im Fenster {start}..{end}. Neuester Tag ({latest['date']}):")
    for k, v in latest.items():
        print(f"  {k}: {v}")
    _replace_dates_and_write(DAILY_CSV, DAILY_FIELDS, daily_rows)

    breakdown_rows = [
        {
            "date": r["date"].isoformat(), "ref_pair": r["ref_pair"], "checked_currency": r["checked_currency"],
            "move_pct": round(float(r["move_pct"]), 6), "vote_agrees": bool(r["vote_agrees"]),
        }
        for _, r in detail.iterrows()
    ]
    latest_detail = [r for r in breakdown_rows if r["date"] == latest["date"]]
    print(f"\n{len(latest_detail)} Referenzpaar-Zeilen fuer {latest['date']}:")
    for r in latest_detail:
        print(f"  {r['ref_pair']} ({r['checked_currency']}): move={r['move_pct']:+.3%} agrees={r['vote_agrees']}")
    _replace_dates_and_write(BREAKDOWN_CSV, BREAKDOWN_FIELDS, breakdown_rows)

    print(f"\nGespeichert: {DAILY_CSV} ({len(daily_rows)} Tage)\nGespeichert: {BREAKDOWN_CSV} ({len(breakdown_rows)} Zeilen)")


if __name__ == "__main__":
    main()
