"""First honest backtest of the 4-indicator checklist strategy, EUR/USD M15,
as manually traded/described by the user: Nadaraya-Watson Envelope (h=8,
mult=3, non-repainting) pre-filter -> RSI Multi-Length [LuxAlgo] (10-20,
70/30) confirmation -> RSI(14)+SMA(14) crossover entry -> ATR(3)x2.5 stop,
fixed 1:2 R:R target, move to breakeven at 1:1 R:R. Confirmations expire
after 8 bars each; opposite-direction breakouts override the pending chain;
multiple overlapping positions are allowed by design.

Uses the same yearly-walk-forward methodology as the other research_*.py
scripts for consistency, though this is the strategy's first-ever
systematic test (no prior tuning to be wary of re-peeking at).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from checklist_strategy.backtest import simulate_checklist_trades
from checklist_strategy.pipeline import run_checklist_pipeline
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2026))


def run_one(df: pd.DataFrame, label: str, **pipeline_kwargs):
    signaled = run_checklist_pipeline(df, **pipeline_kwargs)
    trades = simulate_checklist_trades(signaled)

    print(f"\n{'=' * 10} {label} {'=' * 10}")
    print(f"Total trades: {len(trades)}")
    if trades.empty:
        return None
    print("Exit reason breakdown:\n", trades["exit_reason"].value_counts())

    full_summary = summarize(trades, signaled.index)
    print("\nFull-period summary:")
    for k, v in full_summary.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")

    rows = []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        yr_trades = trades[trades["entry_time"].dt.year == year]
        if yr_trades.empty:
            rows.append({"year": year, "n_trades": 0})
            continue
        s = summarize(yr_trades, yr_df.index)
        rows.append(
            {
                "year": year, "n_trades": s["n_trades"], "win_rate": s["win_rate"],
                "avg_return_bps": s["avg_return_pct"] * 1e4, "sharpe": s["sharpe"],
            }
        )
    yearly = pd.DataFrame(rows).set_index("year")
    print("\nYearly walk-forward:\n", yearly)
    active = yearly[yearly["n_trades"] > 0]
    if not active.empty:
        print(f"Mean Sharpe across active years: {active['sharpe'].mean():.2f}")
        print(f"Years with positive avg return: {(active['avg_return_bps'] > 0).sum()}/{len(active)}")
    return full_summary


def main():
    print("Loading EUR/USD M15 history (cached after first run)...")
    df = fetch_pair_history("EURUSD", "2016-07-28", "2026-07-28")

    run_one(df, "Baseline (no regime filter)", use_regime_filter=False)
    run_one(
        df, "Regime filter: ADX<25 only (no volatility condition)",
        use_regime_filter=True, regime_require_not_trending=True, regime_require_volatile=False,
    )
    run_one(
        df, "Regime filter: ATR-above-median only (no trend condition)",
        use_regime_filter=True, regime_require_not_trending=False, regime_require_volatile=True,
    )
    run_one(
        df, "Regime filter: both (ADX<25 AND volatile)",
        use_regime_filter=True, regime_require_not_trending=True, regime_require_volatile=True,
    )


if __name__ == "__main__":
    main()
