"""Research script: CFTC COT-sentiment filter for the Gold Asian-Range
Breakout (2026-08-08, extracted from Zhang & Laws (2013), "Investor
Sentiment and Forecasting Ability: Evidence from COT Reports in Precious
Metal Futures Markets" - see app_pages/goldi_papers_202608.py tab 5).

The paper's own finding: commercial-trader sentiment (Wang 2001 index,
rolling 3-year percentile-rank of net position) is NEGATIVELY correlated
with returns (commercials are contrarians/hedgers - sell rallies, buy dips),
non-commercial/non-reporting sentiment is POSITIVELY correlated (trend
followers). Granger causality shows sentiment does NOT lead returns -
returns lead sentiment. Despite that, the paper's own mechanical trading
rule (long when commercial sentiment is bullish, i.e. above its own rolling
median) outperformed naive buy-and-hold 1999-2012.

Two hypotheses tested here as a directional ALIGNMENT FILTER on top of the
Asian-Range Breakout's own breakout signal (same structure as the SMA200
trend-bias filter):
1. COMMERCIAL convention (paper's own rule): long breakout aligned with
   bullish (above-median) commercial sentiment, short aligned with bearish.
2. NON-COMMERCIAL convention (mirror hypothesis, since commercial/non-
   commercial sentiment correlate at ~-0.99 in the original paper): long
   aligned with bullish non-commercial sentiment.

Same discipline as every other filter test in this repo: tested against the
current best-known config (ADX<15 + SMA200 trend-bias + max_delay_bars=3),
a window sensitivity sweep (104/156/208 weeks = 2/3/4 years), IS/OOS split,
and an outlier-sensitivity check before trusting any single number."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.cot import fetch_cot_gold, wang_sentiment_index
from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_trend_bias_filter,
    attach_cot_sentiment,
)
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
COT_START = "2011-01-01"  # earlier start so 3/4-year rolling windows have run-up data from 2016
SPLIT = "2021-01-01"
WINDOWS_WEEKS = [104, 156, 208]  # 2y / 3y (paper default) / 4y


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    trades = apply_adx_filter(simulate_asian_breakout(df), adx_min=15)
    daily_close = df["close"].tz_localize(None).resample("D").last().dropna()
    trades = apply_trend_bias_filter(trades, daily_close, sma_window=200)
    trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    print(f"{len(trades)} trades in the current best-known config (ADX + Trend-Bias + Delay<=3).\n")

    print(f"Fetching CFTC COT Gold {COT_START} -> {END} ...")
    cot = fetch_cot_gold(COT_START, END)
    print(f"{len(cot)} weekly COT reports fetched.\n")

    is_long = trades["direction"] == "long"

    # =========================================================================
    # 1. COMMERCIAL convention: window sweep (full period)
    # =========================================================================
    print("=" * 78)
    print("1. COMMERCIAL-SENTIMENT ALIGNMENT (paper's own convention) -- window sweep")
    print("=" * 78)
    print("Aligned = long while commercial SI > its own rolling median, short while below")
    print(f"{'weeks':>6}  {'aligned':<28}  {'counter':<28}")
    for w in WINDOWS_WEEKS:
        si = wang_sentiment_index(cot["comm_net"], window_weeks=w)
        t = attach_cot_sentiment(trades, si, colname="comm_si")
        t = t.dropna(subset=["comm_si"])
        median = t["comm_si"].median()
        bullish = t["comm_si"] > median
        is_long_t = t["direction"] == "long"
        aligned = (is_long_t & bullish) | (~is_long_t & ~bullish)
        print(f"{w:>6}  {fmt(trade_stats(t[aligned])):<28}  {fmt(trade_stats(t[~aligned])):<28}")

    # =========================================================================
    # 2. NON-COMMERCIAL convention: window sweep (full period)
    # =========================================================================
    print("\n" + "=" * 78)
    print("2. NON-COMMERCIAL-SENTIMENT ALIGNMENT (mirror hypothesis) -- window sweep")
    print("=" * 78)
    print("Aligned = long while non-commercial SI > its own rolling median, short while below")
    print(f"{'weeks':>6}  {'aligned':<28}  {'counter':<28}")
    for w in WINDOWS_WEEKS:
        si = wang_sentiment_index(cot["noncomm_net"], window_weeks=w)
        t = attach_cot_sentiment(trades, si, colname="noncomm_si")
        t = t.dropna(subset=["noncomm_si"])
        median = t["noncomm_si"].median()
        bullish = t["noncomm_si"] > median
        is_long_t = t["direction"] == "long"
        aligned = (is_long_t & bullish) | (~is_long_t & ~bullish)
        print(f"{w:>6}  {fmt(trade_stats(t[aligned])):<28}  {fmt(trade_stats(t[~aligned])):<28}")

    # =========================================================================
    # 3. Primary candidate (whichever of 1/2 looks most consistent): IS/OOS
    # =========================================================================
    # Picked after inspecting the sweep above - defaulting to the paper's own
    # convention (commercial, 156 weeks = 3 years); adjust if the sweep points
    # elsewhere.
    W_PRIMARY = 156
    print("\n" + "=" * 78)
    print(f"3. COMMERCIAL-SENTIMENT ALIGNMENT -- IS/OOS breakdown at {W_PRIMARY} weeks")
    print("=" * 78)
    si = wang_sentiment_index(cot["comm_net"], window_weeks=W_PRIMARY)
    t = attach_cot_sentiment(trades, si, colname="comm_si").dropna(subset=["comm_si"])
    median = t["comm_si"].median()
    bullish = t["comm_si"] > median
    is_long_t = t["direction"] == "long"
    aligned_mask = (is_long_t & bullish) | (~is_long_t & ~bullish)
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
