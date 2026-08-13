"""IS/OOS-Verifikation des staerksten Funds aus research_cls_practical_
filter_relaxation.py (2026-08-12): "ohne Rates-Filter" verdoppelt fast die
Trade-Anzahl UND verbessert Ø R UND Gesamtertrag gegenueber der 3-Filter-
Baseline (Voll-Zeitraum). Bevor das uebernommen wird: haelt der Effekt auf
beiden Haelften einzeln (IS 2018-12/2022-06, OOS 2022-06/2026-08), oder ist
es nur ein In-Sample-Artefakt wie der max_total_risk_pct-Fund beim OU-Modell?

min_adx explizit auf None gepinnt (siehe Chat, 2026-08-12) -- isoliert von
der parallel dazugekommenen ADX-Erweiterung."""

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
NO_ADX = {"min_adx": None}


def report(trades: pd.DataFrame, label: str) -> None:
    print(f"\n{'=' * 15} {label} {'=' * 15}")
    if trades.empty:
        print("Keine Trades.")
        return
    r_all = trades["pnl_usd"] / trades["risk_amount_usd"]

    def seg_stats(mask_label: str, sub: pd.DataFrame) -> None:
        n = len(sub)
        if n == 0:
            print(f"  {mask_label}: keine Trades")
            return
        r = sub["pnl_usd"] / sub["risk_amount_usd"]
        wins = r[r > 0]
        years = (pd.Timestamp(sub["entry_time"].max()) - pd.Timestamp(sub["entry_time"].min())).days / 365.25
        print(f"  {mask_label}: n={n} ({n/years:.1f}/Jahr) WR={len(wins)/n*100:.1f}% "
              f"avg_R={r.mean():+.3f} total_R={r.sum():+.2f} PnL=${sub['pnl_usd'].sum():+,.0f}")

    seg_stats("Gesamt", trades)
    seg_stats(f"In-Sample ({START} -> {SPLIT})", trades[trades["entry_time"] < SPLIT])
    seg_stats(f"Out-of-Sample ({SPLIT} -> {END})", trades[trades["entry_time"] >= SPLIT])

    print("  --- Jahresaufschluesselung ---")
    t = trades.copy()
    t["year"] = t["entry_time"].dt.year
    t["r"] = r_all
    rows = []
    for year, g in t.groupby("year"):
        wins = g[g["r"] > 0]
        rows.append({"year": year, "n_trades": len(g), "win_rate": len(wins)/len(g) if len(g) else float("nan"),
                      "avg_r": g["r"].mean(), "total_pnl_usd": g["pnl_usd"].sum()})
    yearly = pd.DataFrame(rows)
    print(yearly.to_string(index=False))
    print(f"  {(yearly['total_pnl_usd'] > 0).sum()}/{len(yearly)} Jahre netto positiv.")


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    args = (eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    baseline = simulate_cls_practical(*args, **NO_ADX)
    report(baseline, "Baseline (alle 3 Filter)")

    no_rates = simulate_cls_practical(*args, use_rates_filter=False, **NO_ADX)
    report(no_rates, "OHNE Rates-Filter")


if __name__ == "__main__":
    main()
