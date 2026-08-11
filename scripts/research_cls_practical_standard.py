"""Standard report (full period, IS/OOS split, per-year breakdown - same
discipline as every other research_*.py script in this repo, e.g.
research_cls_settle_breakout.py) for cls_practical, after the 2026-08-11
threshold sweep + diagnosis: SMA100, rates_z_threshold=0.0, min_sl_atr_mult=1.0
now the defaults. Compares three variants the user asked for:
- Baseline (new defaults, both setups, no BE)
- + Break-even at 0.5R
- Reversal-only
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from presettle_breakout.data import fetch_m5_berlin
from strategy.cls_advanced import PAIRS
from strategy.metrics import summarize, trade_stats

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def report(label: str, trades: pd.DataFrame, index: pd.DatetimeIndex):
    print(f"\n{'=' * 15} {label} {'=' * 15}")
    if trades.empty:
        print("Keine Trades.")
        return

    full = summarize(trades, index)
    print("\n--- Gesamtzeitraum ---")
    for k, v in full.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")
    print(f"  exit_reason_counts: {full['exit_reason_counts']}")
    print(f"  total_pnl_usd: {trades['pnl_usd'].sum():.2f}")

    is_trades = trades[trades["entry_time"] < SPLIT]
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    print(f"\n--- In-Sample ({START} -> {SPLIT}) ---")
    is_stats = trade_stats(is_trades)
    for k, v in is_stats.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")
    print(f"  total_pnl_usd: {is_trades['pnl_usd'].sum():.2f}")

    print(f"\n--- Out-of-Sample ({SPLIT} -> {END}) ---")
    oos_stats = trade_stats(oos_trades)
    for k, v in oos_stats.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")
    print(f"  total_pnl_usd: {oos_trades['pnl_usd'].sum():.2f}")

    print("\n--- Jahresaufschlüsselung ---")
    t = trades.copy()
    t["year"] = t["entry_time"].dt.year
    rows = []
    for year, g in t.groupby("year"):
        s = trade_stats(g)
        rows.append(
            {
                "year": year, "n_trades": s["n_trades"], "win_rate": s["win_rate"],
                "profit_factor": s["profit_factor"], "total_pnl_usd": g["pnl_usd"].sum(),
            }
        )
    yearly = pd.DataFrame(rows)
    print(yearly.to_string(index=False))
    n_pos = (yearly["total_pnl_usd"] > 0).sum()
    print(f"\n{n_pos}/{len(yearly)} Jahre netto positiv.")


def main():
    eurusd_m5 = fetch_m5_berlin("EURUSD", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    baseline = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    report("Baseline (SMA100, z=0.0, min_sl_atr=1.0)", baseline, eurusd_m5.index)

    be_variant = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, be_trigger_r=0.5)
    report("+ Break-Even ab 0.5R", be_variant, eurusd_m5.index)

    reversal_only = simulate_cls_practical(
        eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, allowed_setups=("reversal",)
    )
    report("Reversal-Only", reversal_only, eurusd_m5.index)


if __name__ == "__main__":
    main()
