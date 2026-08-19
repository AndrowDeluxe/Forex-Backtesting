"""EUR/USD-only Re-Test des Rates-("Zins"-)Filters auf TAGESKERZEN-Basis
(User-Anfrage 2026-08-19): "wir hatten den Zinsfilter auf Tagesbasis
schoneinmal gebaut und verworfen [...] evtl können wir da nochmal was
anpassen [...] zum Beispiel die Richtung der letzten Tageskerze als
Validierung fuer unseren Trade".

Rekonstruktion/Kontext (siehe knowledge/projects/bond-yield-spread-indikator.md):
der fruehere Zinsfilter (bond_yield_indicator/, FRED-basiert) scheiterte
NICHT am Framework, sondern an der Datenaufloesung - 6 von 7 Laendern sind
auf FRED nur MONATLICH verfuegbar (heute 2026-08-19 erneut verifiziert: DE
zuletzt 2026-06-01). Eine "letzte Tageskerze" ist auf einer monatlichen
Serie bedeutungslos. Diese Version nutzt stattdessen die BUND/USTBOND-CFDs
(dieselbe Datenquelle, die der bereits vorhandene, aber deaktivierte
Intraday-Ampel-Filter in cls_practical/rates.py::compute_rate_support_score
nutzt) - die aktualisieren taeglich/intraday, kein Aufloesungsproblem.

Unterschied zur bestehenden Ampel: compute_rate_support_score liest den
GLEICHEN Tag (06:00-09:00 Settle-Fenster), compute_daily_rate_score (neu)
liest den VOLLEN Vortag (00:00-24:00 Berlin), per lag_days verschoben -
eine echte Leading-/Vortages-Validierung statt eines Now-Cast.

Getestete "Validierungsmoeglichkeiten" (User-Wunsch, mehrere Varianten):
- lag_days: 1 (User-Beispiel: "die Richtung der letzten Tageskerze"), 2, 3
  Kalendertage zurueck.
- rates_z_threshold: 0.0 (reiner Richtungs-Check, wie beim bestehenden
  Ampel-Filter-Default), 0.25, 0.5 (zusaetzliche Mindest-Staerke-Schwelle
  relativ zur rollierenden 60-Tage-Streuung).
- filter_mode: "and" (muss zusammen mit Trend+Cross uebereinstimmen) vs.
  "majority" (mind. 2 von 3 der aktiven Filter).

GEGEN die validierte Baseline (use_rates_filter=False, kein Zinsfilter) auf
EUR/USD, IS-Auswahl (2018-12/2022-06) -> OOS-Validierung (2022-06/2026-08),
identisch zur Methodik ueberall sonst in diesem Projekt."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from cls_practical.rates import compute_daily_rate_score

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in cls_advanced.PAIRS if p != "EURUSD"]


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        return {"label": label, "n": 0, "avg_r": float("nan"), "n_is": 0, "avg_r_is": float("nan"), "n_oos": 0, "avg_r_oos": float("nan")}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    row = {
        "label": label, "n": n, "win_rate": win_rate * 100, "avg_r": r.mean(), "profit_factor": pf,
        "total_pnl": trades["pnl_usd"].sum(), "n_is": int(is_mask.sum()),
        "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }
    print(f"  {label:38s}: n={row['n']:>3d} WR={row['win_rate']:5.1f}% avg_R={row['avg_r']:+.3f} PF={row['profit_factor']:.2f} "
          f"PnL=${row['total_pnl']:+,.0f} | IS(n={row['n_is']:>3d}) avg_R={row['avg_r_is']:+.3f} | "
          f"OOS(n={row['n_oos']:>3d}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    print("\n" + "=" * 100 + "\nBASELINE (kein Zinsfilter)\n" + "=" * 100)
    baseline_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, use_rates_filter=False)
    baseline = stats(baseline_trades, "Baseline (use_rates_filter=False)")

    rows = [baseline]
    print("\n" + "=" * 100 + "\nTAGESKERZEN-ZINSFILTER: lag_days x z_threshold x filter_mode\n" + "=" * 100)
    for lag_days in (1, 2, 3):
        score = compute_daily_rate_score(bund_m5, ustbond_m5, lag_days=lag_days)
        for z_threshold in (0.0, 0.25, 0.5):
            for filter_mode in ("and", "majority"):
                label = f"lag={lag_days}d z>={z_threshold} mode={filter_mode}"
                trades = simulate_cls_practical(
                    eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                    use_rates_filter=True, rates_score_override=score,
                    rates_z_threshold=z_threshold, filter_mode=filter_mode,
                )
                row = stats(trades, label)
                row.update({"lag_days": lag_days, "z_threshold": z_threshold, "filter_mode": filter_mode})
                rows.append(row)

    df = pd.DataFrame(rows)
    variant_rows = df[df["label"] != baseline["label"]]
    both_beat = variant_rows[
        (variant_rows["avg_r_is"] > baseline["avg_r_is"]) & (variant_rows["avg_r_oos"] > baseline["avg_r_oos"])
    ]
    print(f"\nBaseline: IS avg_R={baseline['avg_r_is']:+.3f} -> OOS avg_R={baseline['avg_r_oos']:+.3f}")
    print(f"\nVarianten, die die Baseline auf IS UND OOS GLEICHZEITIG schlagen ({len(both_beat)}):")
    if len(both_beat) == 0:
        print("  keine")
    else:
        for _, r in both_beat.sort_values("avg_r_is", ascending=False).iterrows():
            print(f"  {r['label']:38s}: IS avg_R={r['avg_r_is']:+.3f} (n={r['n_is']:.0f}) -> "
                  f"OOS avg_R={r['avg_r_oos']:+.3f} (n={r['n_oos']:.0f})")

    if len(variant_rows.dropna(subset=["avg_r_is"])) > 0:
        winner = variant_rows.loc[variant_rows["avg_r_is"].idxmax()]
        print(f"\nIS-Gewinner: {winner['label']} (IS avg_R={winner['avg_r_is']:+.3f}) -> "
              f"OOS avg_R={winner['avg_r_oos']:+.3f} (n_oos={winner['n_oos']:.0f})")

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_daily_rate_filter_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
