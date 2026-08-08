"""Research script for the CLS-Settle-Breakout variant (asian_range_breakout/
cls_settle.py) - full-period stats, IS/OOS split, per-year breakdown, same
discipline as every other strategy in this repo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.cls_settle import fetch_gold_m15_berlin, simulate_cls_settle_breakout
from strategy.metrics import summarize, trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"


def main():
    print(f"Fetching GOLD M15 (Berlin tz) {START} -> {END} ...")
    df = fetch_gold_m15_berlin(START, END)
    print(f"{len(df)} bars fetched.")

    trades = simulate_cls_settle_breakout(df)
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
    for k, v in trade_stats(is_trades).items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")
    print(f"\n=== Out-of-Sample ({SPLIT} -> {END}) ===")
    for k, v in trade_stats(oos_trades).items():
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
    print(f"\n{(yearly['total_return_pct'] > 0).sum()}/{len(yearly)} years net positive.")
    print(f"Median trade return_pct: {trades['return_pct'].median():.5f}")


if __name__ == "__main__":
    main()
