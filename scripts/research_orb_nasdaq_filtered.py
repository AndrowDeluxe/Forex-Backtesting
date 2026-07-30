"""Tests the two filters the Nasdaq ORB deep-dive suggested: long-only (the
edge was almost entirely on the long side, short ~breakeven) and an
ADX>=25-at-entry floor (the regime_decomposition found ADX mattered more
than the volatility-tercile axis). Compares baseline vs. long-only vs.
long-only+ADX>=25, same yearly walk-forward reporting as every other
research_*.py script here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2027))
START, END = "2016-07-28", "2026-07-28"
STOP_MULT = 2.0


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def run_one(signaled: pd.DataFrame, label: str):
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)

    print(f"\n{'=' * 10} {label} {'=' * 10}")
    print(f"Total trades: {len(trades)}")
    if trades.empty:
        return
    full = summarize(trades, signaled.index)
    print("Full-period:", {k: v for k, v in full.items() if k != "exit_reason_counts"})

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
                "profit_factor": s["profit_factor"],
            }
        )
    yearly = pd.DataFrame(rows).set_index("year")
    print(yearly)
    active = yearly[yearly["n_trades"] > 0]
    if not active.empty:
        print(f"Mean Sharpe across active years: {active['sharpe'].mean():.2f}")
        print(f"Years with positive avg return: {(active['avg_return_bps'] > 0).sum()}/{len(active)}")


def main():
    print("Loading NASDAQ M15 (cached after first run)...")
    df = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))

    baseline = run_orb_pipeline(df, atr_n=14, atr_mult=1.0)
    run_one(baseline, "Baseline (Long+Short, kein ADX-Filter)")

    long_only = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True)
    run_one(long_only, "Long-only")

    long_adx = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    run_one(long_adx, "Long-only + ADX>=25 bei Entry")


if __name__ == "__main__":
    main()
