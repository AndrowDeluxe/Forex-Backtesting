"""Systematischer Sweep aller bisher ausgelassenen Optimierungsparameter
(User-Anfrage 2026-08-13, siehe Chat-Tabelle) fuer cls_practical, auf der
JETZT aktuellen Baseline (use_rates_filter=False, min_adx=15.0, Cross an,
filter_mode="and", Reversal+Continuation). Alles NUR auf In-Sample
(2018-12-01 bis 2022-06-01) -- Out-of-Sample bleibt fuer die abschliessende
Verifikation des besten Gesamt-Kandidaten reserviert, sonst verbrennt der
Holdout seinen Zweck (Projekt-Disziplin, siehe OU-Modell/London-Range).

Sequenzielle Ein-Parameter-Sweeps (jeweils alle anderen auf dem aktuellen
Default gehalten), nicht vollstaendiger Kreuzprodukt-Grid -- bei 6 Dimensionen
waere das nicht mehr handhabbar. Am Ende: bester gefundener Kandidat wird
EINMALIG auf OOS geprueft (separates Skript/Aufruf).

Ausgelassen (Infrastruktur-Aufwand zu hoch fuer diesen Durchlauf, hier
dokumentiert statt stillschweigend uebersprungen):
- Cross-Filter-Timeframe (nur M15-Fetch fuer die Majors vorhanden)
- Teilmenge der 5 Majors fuer den Cross-Filter (bräuchte Aenderung an
  compute_cross_confirmation's Signatur)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def r_stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"  {label}: keine Trades")
        return {"label": label, "n_trades": 0, "avg_r": float("nan"), "total_r": 0.0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins = r[r > 0]
    row = {"label": label, "n_trades": n, "win_rate": len(wins) / n, "avg_r": r.mean(), "total_r": r.sum()}
    print(f"  {label}: n={n} WR={row['win_rate']*100:.1f}% avg_R={row['avg_r']:+.3f} total_R={row['total_r']:+.2f}")
    return row


def main():
    print("Lade Daten (M5/M3/M15 EUR/USD, Majors, Rates)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, SPLIT)
    eurusd_m3 = fetch_eurusd_entry_tf_berlin("M3", START, SPLIT)
    eurusd_m15 = fetch_eurusd_entry_tf_berlin("M15", START, SPLIT)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, SPLIT) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, SPLIT)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, SPLIT)
    args5 = (eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    all_rows = []

    print("\n=== 1) TP-Modus: adr_mult (aktuell 0.35) ===")
    for m in (0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        row = r_stats(simulate_cls_practical(*args5, adr_mult=m), f"adr_mult={m}")
        row["group"] = "adr_mult"
        all_rows.append(row)

    print("\n=== 2) TP-Modus: adr_period (aktuell 14) ===")
    for p in (7, 14, 21, 28):
        row = r_stats(simulate_cls_practical(*args5, adr_period=p), f"adr_period={p}")
        row["group"] = "adr_period"
        all_rows.append(row)

    print("\n=== 3) TP-Modus: fixed_r statt adr (rr_fixed-Sweep) ===")
    for rr in (1.0, 1.5, 2.0, 2.5, 3.0):
        row = r_stats(simulate_cls_practical(*args5, tp_mode="fixed_r", rr_fixed=rr), f"fixed_r, rr={rr}")
        row["group"] = "tp_mode_fixed_r"
        all_rows.append(row)

    print("\n=== 4) Trend-Filter: min_adx (aktuell 15.0) ===")
    for adx in (0, 5, 10, 15, 20, 25, 30):
        row = r_stats(simulate_cls_practical(*args5, min_adx=(adx if adx > 0 else None)), f"min_adx={adx}")
        row["group"] = "min_adx"
        all_rows.append(row)

    print("\n=== 5) Trend-Filter: adx_period (aktuell 14) ===")
    for p in (7, 14, 21, 28):
        row = r_stats(simulate_cls_practical(*args5, adx_period=p), f"adx_period={p}")
        row["group"] = "adx_period"
        all_rows.append(row)

    print("\n=== 6) Entry-Cutoff (aktuell 12:00) ===")
    for cutoff in ("10:00", "11:00", "12:00", "13:00", "14:00"):
        row = r_stats(simulate_cls_practical(*args5, entry_cutoff=cutoff), f"entry_cutoff={cutoff}")
        row["group"] = "entry_cutoff"
        all_rows.append(row)

    print("\n=== 7) min_sl_atr_mult (aktuell 1.0, neu unter aktueller Config) ===")
    for m in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0):
        row = r_stats(simulate_cls_practical(*args5, min_sl_atr_mult=m), f"min_sl_atr_mult={m}")
        row["group"] = "min_sl_atr_mult"
        all_rows.append(row)

    print("\n=== 8) Entry-Timeframe M3/M5/M15 (neu unter aktueller Config) ===")
    for tf, df in (("M3", eurusd_m3), ("M5", eurusd_m5), ("M15", eurusd_m15)):
        row = r_stats(simulate_cls_practical(df, other_majors_m15, bund_m5, ustbond_m5), f"timeframe={tf}")
        row["group"] = "timeframe"
        all_rows.append(row)

    print("\n=== 9) Kosten-Stresstest: spread_bps (aktuell 0.3) ===")
    for sb in (0.3, 0.6, 1.0, 1.5, 2.0):
        row = r_stats(simulate_cls_practical(*args5, spread_bps=sb), f"spread_bps={sb}")
        row["group"] = "spread_bps"
        all_rows.append(row)

    print("\n=== 10) Kosten-Stresstest: slippage_bps (aktuell 0.0) ===")
    for sl in (0.0, 0.5, 1.0, 2.0):
        row = r_stats(simulate_cls_practical(*args5, slippage_bps=sl), f"slippage_bps={sl}")
        row["group"] = "slippage_bps"
        all_rows.append(row)

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "full_param_sweep_in_sample.csv"
    pd.DataFrame(all_rows).to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
