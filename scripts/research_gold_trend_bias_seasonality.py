"""Research script: two more "151 Trading Strategies" ideas tested against
the Gold Asian-Range Breakout (2026-08-08 follow-up to
research_gold_dxy_vix_change_filters.py, which rejected the DXY-alignment
and VIX-change-rate hypotheses).

1. Daily-trend-bias filter (Time-Series Momentum / CTA Trendfolge, paper
   chapter 10.4 - already built as its own strategy in `triple_ma`, but
   never tried as a DIRECTIONAL BIAS on top of an existing strategy).
   Hypothesis: Asian-range breakouts that fire IN the direction of Gold's
   own prevailing daily trend (long above its SMA, short below it) should
   hold up better than counter-trend breakouts - the classic "trade
   breakouts with the trend, fade them against it" logic.
2. Seasonality (Commodities chapter, weekday/month effects) - a quick,
   heavily caveated descriptive check, not a real hypothesis with a
   plausible mechanism for THIS specific session-breakout strategy (unlike
   agricultural harvest cycles), included mainly for completeness per the
   paper's chapter.

Same discipline as every other filter test in this repo: tested against the
ADX<15-filtered production config (not the raw baseline), full period, IS/OOS
split (2021-01-01), a SMA-window sensitivity sweep, an outlier-sensitivity
check (does removing the single best trade wipe out the edge?), and an
expanding-window walk-forward test (same pattern already used to validate
the ADX filter, asian_range_breakout/walkforward.py) before trusting a
single-cut number."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter, attach_trend_bias
from asian_range_breakout.walkforward import run_trend_bias_walk_forward
from strategy.metrics import summarize, trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
SMA_WINDOWS = [50, 100, 150, 200]
PRIMARY_SMA = 200


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    trades_all = simulate_asian_breakout(df)
    trades = apply_adx_filter(trades_all, adx_min=15)
    print(f"{len(trades_all)} raw trades, {len(trades)} after the production ADX<15 filter.")

    # Daily close series (NY calendar day, tz-naive index) built from the same
    # Dukascopy M15 feed - no new/extra data source, no methodological drift.
    daily_close = df["close"].tz_localize(None).resample("D").last().dropna()

    # =========================================================================
    # 1. Trend-bias filter: SMA-window sensitivity sweep (full period)
    # =========================================================================
    print("\n" + "=" * 78)
    print("1. DAILY-TREND-BIAS FILTER -- SMA-window sensitivity sweep (full period)")
    print("=" * 78)
    print("Aligned    = long while prior-day close > SMA, short while prior-day close < SMA")
    print("Counter    = long while prior-day close < SMA, short while prior-day close > SMA")
    print(f"{'SMA':>6}  {'aligned (with trend)':<28}  {'counter-trend':<28}")
    for w in SMA_WINDOWS:
        t = attach_trend_bias(trades, daily_close, sma_window=w)
        print(
            f"{w:>6}  {fmt(trade_stats(t[t['aligned']])):<28}  {fmt(trade_stats(t[~t['aligned']])):<28}"
        )

    # =========================================================================
    # 2. Trend-bias filter: full IS/OOS breakdown at the primary SMA window
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"2. DAILY-TREND-BIAS FILTER -- IS/OOS breakdown at SMA={PRIMARY_SMA}")
    print("=" * 78)
    t = attach_trend_bias(trades, daily_close, sma_window=PRIMARY_SMA)
    aligned_mask = t["aligned"]
    is_period = t["entry_time"] < SPLIT
    oos_period = t["entry_time"] >= SPLIT

    print(f"{'':<12}{'Aligned':<28}{'Counter-trend':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(t[aligned_mask])):<28}{fmt(trade_stats(t[~aligned_mask])):<28}")
    print(
        f"{'IS':<12}{fmt(trade_stats(t[aligned_mask & is_period])):<28}"
        f"{fmt(trade_stats(t[~aligned_mask & is_period])):<28}"
    )
    print(
        f"{'OOS':<12}{fmt(trade_stats(t[aligned_mask & oos_period])):<28}"
        f"{fmt(trade_stats(t[~aligned_mask & oos_period])):<28}"
    )

    # =========================================================================
    # 3. Full risk-metric comparison + outlier-sensitivity check
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"3. FULL METRICS: ADX-only baseline vs. ADX+Trend-aligned (SMA={PRIMARY_SMA})")
    print("=" * 78)
    aligned_trades = t[aligned_mask]
    base_stats = summarize(trades, df.index)
    aligned_stats = summarize(aligned_trades, df.index)
    for k in ["n_trades", "win_rate", "profit_factor", "sharpe", "max_drawdown", "cagr"]:
        print(f"  {k:<16} baseline={base_stats[k]!s:<12} aligned={aligned_stats[k]!s:<12}")

    sorted_ret = aligned_trades.sort_values("return_pct", ascending=False)
    without_best = aligned_trades.drop(sorted_ret.index[0])
    print(f"\n  Best single trade return_pct: {sorted_ret['return_pct'].iloc[0]:+.2%}")
    print(f"  PF with best trade:    {trade_stats(aligned_trades)['profit_factor']:.3f}")
    print(f"  PF without best trade: {trade_stats(without_best)['profit_factor']:.3f}")
    print("  (if PF collapses to <=1.0 without it, the edge is outlier-driven, not robust)")

    # =========================================================================
    # 4. Walk-forward validation (expanding window, same pattern as ADX filter)
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"4. WALK-FORWARD VALIDATION (expanding window, SMA={PRIMARY_SMA})")
    print("=" * 78)
    print(
        "For each test year, only trades BEFORE that year decide whether 'aligned' beats "
        "'counter-trend' on their own (min. 100 trades/bucket) - filter applied forward only if "
        "training confirms it. No hindsight from the full sample."
    )
    wf = run_trend_bias_walk_forward(t, start_test_year=2019, end_test_year=2026)
    print(wf.to_string(index=False))
    n_confirmed = wf["filter_confirmed_on_train"].sum()
    n_positive = (wf["pf_walkforward"] > 1.0).sum()
    print(f"\nFilter confirmed on training data in {n_confirmed}/{len(wf)} test years.")
    print(f"{n_positive}/{len(wf)} test years ended with PF>1.0 under the walk-forward rule.")

    # =========================================================================
    # 5. Seasonality: weekday and month-of-year (descriptive, heavily caveated)
    # =========================================================================
    print("\n" + "=" * 78)
    print("5. SEASONALITY -- weekday of entry (full period, ADX-filtered trades)")
    print("=" * 78)
    ts = trades.copy()
    ts["weekday"] = ts["entry_time"].dt.day_name()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for wd in weekday_order:
        g = ts[ts["weekday"] == wd]
        print(f"{wd:<10} {fmt(trade_stats(g))}")

    print("\n" + "=" * 78)
    print("6. SEASONALITY -- month of entry (full period, ADX-filtered trades)")
    print("=" * 78)
    ts["month"] = ts["entry_time"].dt.month
    for m in range(1, 13):
        g = ts[ts["month"] == m]
        print(f"Month {m:>2}  {fmt(trade_stats(g))}")


if __name__ == "__main__":
    main()
