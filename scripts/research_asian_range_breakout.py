"""Research script for asian_range_breakout (Gold XAUUSD, source:
Gold_Asian_Breakout_Strategy.txt) - full-period stats, IS/OOS split, and a
per-year breakdown, same discipline as every other strategy in this repo
(don't trust a single pooled number, check it survives a genuine
out-of-sample look and isn't carried by one or two years)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from strategy.metrics import summarize, trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    print(f"{len(df)} bars fetched.")

    trades = simulate_asian_breakout(df)
    print(f"\n{len(trades)} trades generated (full period).")

    print("\n=== Full period ===")
    stats = summarize(trades, df.index)
    for k, v in stats.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")
    print(f"  exit_reason_counts: {stats['exit_reason_counts']}")

    is_trades = trades[trades["entry_time"] < SPLIT]
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    print(f"\n=== In-Sample ({START} -> {SPLIT}) ===")
    is_stats = trade_stats(is_trades)
    for k, v in is_stats.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")

    print(f"\n=== Out-of-Sample ({SPLIT} -> {END}) ===")
    oos_stats = trade_stats(oos_trades)
    for k, v in oos_stats.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")

    print("\n=== Per-year breakdown ===")
    trades = trades.copy()
    trades["year"] = trades["entry_time"].dt.year
    rows = []
    for year, g in trades.groupby("year"):
        s = trade_stats(g)
        rows.append(
            {
                "year": year,
                "n_trades": s["n_trades"],
                "win_rate": s["win_rate"],
                "profit_factor": s["profit_factor"],
                "avg_return_pct": s["avg_return_pct"],
                "total_return_pct": g["return_pct"].sum(),
            }
        )
    yearly = pd.DataFrame(rows)
    print(yearly.to_string(index=False))

    n_years_positive = (yearly["total_return_pct"] > 0).sum()
    print(f"\n{n_years_positive}/{len(yearly)} years net positive.")

    median_r = trades["return_pct"].median()
    print(f"Median trade return_pct: {median_r:.5f}")


if __name__ == "__main__":
    main()
