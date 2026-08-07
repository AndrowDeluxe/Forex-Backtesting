"""Research script: momentum-thrust filter for the Gold Asian-Range Breakout
(2026-08-08, follow-up to the bottleneck diagnosis - user wants a genuinely
forward-usable win-rate/quality lever, not another lookahead artifact like
the close-confirmation dead end).

Idea: measure Gold's own ATR-normalized net directional move over the
`lookback_bars` M15 bars immediately BEFORE the Asian range closes
(window_end) - "was there already real directional thrust heading into the
session, or was price just drifting/chopping". Fully known at window_end,
no lookahead (unlike a same-bar breakout-strength measure).

Two separate hypotheses tested:
1. ALIGNMENT: breakout direction matches the pre-window momentum direction
   (long after an up-thrust, short after a down-thrust) - a short-horizon
   cousin of the already-validated SMA200 trend-bias filter, but measured in
   hours instead of months.
2. MAGNITUDE: raw thrust strength (|momentum_r|) regardless of direction -
   "was Gold already moving with conviction, in either direction, right
   before the session closed" as a proxy for "is this a momentum regime or
   a chop regime" (economically adjacent to ADX, but a different, faster
   construction - worth checking it isn't just redundant with ADX).

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
    attach_pre_window_momentum,
)
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
LOOKBACKS = [4, 8, 16, 24, 48]  # 1h, 2h, 4h, 6h, 12h at M15


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

    # =========================================================================
    # 1. ALIGNMENT hypothesis: lookback sweep (full period)
    # =========================================================================
    print("=" * 78)
    print("1. MOMENTUM-ALIGNMENT -- lookback-window sensitivity sweep (full period)")
    print("=" * 78)
    print("Aligned = long after an up-thrust into the session, short after a down-thrust")
    print(f"{'lookback':>10}  {'aligned':<28}  {'counter':<28}")
    for lb in LOOKBACKS:
        t = attach_pre_window_momentum(trades, df, lookback_bars=lb)
        is_long = t["direction"] == "long"
        aligned_mask = (is_long & (t["momentum_r"] > 0)) | (~is_long & (t["momentum_r"] < 0))
        print(
            f"{lb:>10}  {fmt(trade_stats(t[aligned_mask])):<28}  {fmt(trade_stats(t[~aligned_mask])):<28}"
        )

    # =========================================================================
    # 2. MAGNITUDE hypothesis: lookback sweep (full period), top-tertile vs. rest
    # =========================================================================
    print("\n" + "=" * 78)
    print("2. MOMENTUM-MAGNITUDE (|momentum_r|, direction-agnostic) -- lookback sweep")
    print("=" * 78)
    print("Strong = top tertile of |momentum_r| (biggest pre-window thrust, either direction)")
    print(f"{'lookback':>10}  {'strong':<28}  {'weak':<28}")
    for lb in LOOKBACKS:
        t = attach_pre_window_momentum(trades, df, lookback_bars=lb)
        thresh = t["momentum_r"].abs().quantile(2 / 3)
        strong_mask = t["momentum_r"].abs() >= thresh
        print(
            f"{lb:>10}  {fmt(trade_stats(t[strong_mask])):<28}  {fmt(trade_stats(t[~strong_mask])):<28}"
            f"  (thresh |momentum_r|>={thresh:.2f})"
        )

    # =========================================================================
    # 3. Best candidate (whichever of the two looks most consistent): IS/OOS
    # =========================================================================
    # Chosen after inspecting the sweep output above - picked lookback=8 (2h)
    # for the alignment hypothesis as the primary candidate; adjust if the
    # sweep printed above points elsewhere.
    LB_PRIMARY = 8
    print("\n" + "=" * 78)
    print(f"3. MOMENTUM-ALIGNMENT -- IS/OOS breakdown at lookback={LB_PRIMARY} bars")
    print("=" * 78)
    t = attach_pre_window_momentum(trades, df, lookback_bars=LB_PRIMARY)
    is_long = t["direction"] == "long"
    aligned_mask = (is_long & (t["momentum_r"] > 0)) | (~is_long & (t["momentum_r"] < 0))
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

    # Cross-check: correlation with ADX (is this just redundant with the existing filter?)
    print("\n" + "=" * 78)
    print("4. SANITY CHECK: correlation of |momentum_r| with adx_at_entry")
    print("=" * 78)
    corr = t["momentum_r"].abs().corr(t["adx_at_entry"])
    print(f"Pearson correlation: {corr:.3f} (near 0 = genuinely new information, not redundant with ADX)")


if __name__ == "__main__":
    main()
