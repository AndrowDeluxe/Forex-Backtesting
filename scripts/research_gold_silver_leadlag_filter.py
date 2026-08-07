"""Research script: Gold-Silver lead-lag confirmation filter for the Gold
Asian-Range Breakout (2026-08-08, extracted from Sulistyardi (2026),
"Regime-Conditional Framework for Rolling Correlation and Lead-Lag Analysis
among XAUUSD, XAGUSD, and BTCUSD" - see app_pages/goldi_papers_202608.py
tab 3).

The source paper is a literature synthesis + PROPOSED framework, not an
empirically validated result - it argues (from prior literature, not its
own tests) that silver tends to lead gold in momentum/breakout phases
(higher beta, more speculative order flow) and lags/follows in pure
safe-haven shocks. The simplest directly-testable translation with data
already on hand: does Silver's own recent price direction (rate of change
over a lookback window) predict which way a Gold breakout should be
trusted - i.e. a cross-asset momentum-CONFIRMATION filter, structurally
identical to the already-tested (and rejected) DXY-alignment filter, just
using Silver instead of the Dollar Index.

Same discipline as every other filter test in this repo: tested against the
current best-known config (ADX<15 + SMA200 trend-bias + max_delay_bars=3),
a lookback-window sensitivity sweep, IS/OOS split, and an outlier-sensitivity
check before trusting any single number."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_trend_bias_filter,
    attach_series_change,
)
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
LOOKBACK_DAYS = [1, 3, 5, 10, 20]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    gold_df = fetch_gold_m15(START, END)
    trades = apply_adx_filter(simulate_asian_breakout(gold_df), adx_min=15)
    daily_close_gold = gold_df["close"].tz_localize(None).resample("D").last().dropna()
    trades = apply_trend_bias_filter(trades, daily_close_gold, sma_window=200)
    trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    print(f"{len(trades)} trades in the current best-known config (ADX + Trend-Bias + Delay<=3).\n")

    print(f"Fetching SILVER M15 {START} -> {END} ...")
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()
    print(f"{len(daily_close_silver)} daily Silver closes.\n")

    is_long = trades["direction"] == "long"

    # =========================================================================
    # 1. Silver-momentum alignment: lookback sweep (full period)
    # =========================================================================
    print("=" * 78)
    print("1. SILVER-MOMENTUM ALIGNMENT -- lookback-window sensitivity sweep (full period)")
    print("=" * 78)
    print("Aligned = long Gold while Silver has been rising, short while Silver has been falling")
    print(f"{'days':>6}  {'aligned':<28}  {'counter':<28}")
    for w in LOOKBACK_DAYS:
        t = attach_series_change(trades, daily_close_silver, "silver_chg", window=w)
        t = t.dropna(subset=["silver_chg"])
        is_long_t = t["direction"] == "long"
        aligned = (is_long_t & (t["silver_chg"] > 0)) | (~is_long_t & (t["silver_chg"] < 0))
        print(f"{w:>6}  {fmt(trade_stats(t[aligned])):<28}  {fmt(trade_stats(t[~aligned])):<28}")

    # =========================================================================
    # 2. Primary candidate: IS/OOS (window picked after inspecting sweep above)
    # =========================================================================
    W_PRIMARY = 5
    print("\n" + "=" * 78)
    print(f"2. SILVER-MOMENTUM ALIGNMENT -- IS/OOS breakdown at {W_PRIMARY} days")
    print("=" * 78)
    t = attach_series_change(trades, daily_close_silver, "silver_chg", window=W_PRIMARY)
    t = t.dropna(subset=["silver_chg"])
    is_long_t = t["direction"] == "long"
    aligned_mask = (is_long_t & (t["silver_chg"] > 0)) | (~is_long_t & (t["silver_chg"] < 0))
    is_period = t["entry_time"] < SPLIT
    oos_period = t["entry_time"] >= SPLIT

    print(f"{'':<12}{'Aligned':<28}{'Counter':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(t[aligned_mask])):<28}{fmt(trade_stats(t[~aligned_mask])):<28}")
    print(
        f"{'IS':<12}{fmt(trade_stats(t[aligned_mask & is_period])):<28}"
        f"{fmt(trade_stats(t[~aligned_mask & is_period])):<28}"
    )
    print(
        f"{'OOS':<12}{fmt(trade_stats(t[aligned_mask & oos_period])):<28}"
        f"{fmt(trade_stats(t[~aligned_mask & oos_period])):<28}"
    )

    aligned_trades = t[aligned_mask]
    if len(aligned_trades) > 0:
        sorted_ret = aligned_trades.sort_values("return_pct", ascending=False)
        without_best = aligned_trades.drop(sorted_ret.index[0])
        print(f"\nBest single trade return_pct: {sorted_ret['return_pct'].iloc[0]:+.2%}")
        print(f"PF with best trade:    {trade_stats(aligned_trades)['profit_factor']:.3f}")
        print(f"PF without best trade: {trade_stats(without_best)['profit_factor']:.3f}")


if __name__ == "__main__":
    main()
