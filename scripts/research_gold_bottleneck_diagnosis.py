"""Diagnoses WHERE the Gold Asian-Range Breakout's win rate is actually lost
(2026-08-08, user request: "finde das Bottleneck, wie koennte man die
Win-Rate sinnvoll erhoehen"). Tested against the current best-known config
(ADX<15 filter + SMA200 trend-bias filter). Four angles:

1. Exit-reason breakdown (stops are 100% losers by construction - how much
   of the win-rate problem is just "stops fire too often" vs. something else).
2. Long vs. short split - Gold trended up most of 2016-2026; does the
   strategy's win rate hide a directional asymmetry?
3. Entry delay (bars between window close and breakout fill) vs. outcome -
   does a fast/aggressive breakout behave differently from a slow one?
4. Maximum-Favorable-Excursion (MFE) analysis of STOPPED-OUT trades only -
   re-slices the underlying M15 bars between each trade's entry and exit to
   see how close losers got to being winners before reversing. This is the
   key diagnostic for "would a confirmation entry / wider stop / partial
   take-profit help" - if losers were never close, no amount of stop/target
   tuning will raise the win rate; if many losers got most of the way to 1R
   before reversing, that's a concrete lever."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter, apply_trend_bias_filter
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"


def compute_mfe(df: pd.DataFrame, trades: pd.DataFrame) -> pd.Series:
    """For each trade, the best R-multiple reached between entry and exit
    (inclusive) - NOT just the final R-multiple at exit. Uses the trade's
    own stop_distance as the R unit, same convention as sizing.py."""
    high = df["high"]
    low = df["low"]
    mfe = []
    for _, t in trades.iterrows():
        window = df.loc[t["entry_time"] : t["exit_time"]]
        if window.empty:
            mfe.append(np.nan)
            continue
        if t["direction"] == "long":
            best_move = window["high"].max() - t["entry_price"]
        else:
            best_move = t["entry_price"] - window["low"].min()
        mfe.append(best_move / t["stop_distance"])
    return pd.Series(mfe, index=trades.index)


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    trades = apply_adx_filter(simulate_asian_breakout(df), adx_min=15)
    daily_close = df["close"].tz_localize(None).resample("D").last().dropna()
    trades = apply_trend_bias_filter(trades, daily_close, sma_window=200)
    print(f"{len(trades)} trades in the current best-known config (ADX<15 + SMA200 trend-bias).\n")

    # =========================================================================
    # 1. Exit-reason breakdown
    # =========================================================================
    print("=" * 78)
    print("1. EXIT-REASON BREAKDOWN")
    print("=" * 78)
    for reason, g in trades.groupby("exit_reason"):
        wins = (g["return_pct"] > 0).mean()
        print(f"  {reason:<12} n={len(g):>4}  share={len(g)/len(trades):.1%}  win_rate_within={wins:.1%}")

    # =========================================================================
    # 2. Long vs. short
    # =========================================================================
    print("\n" + "=" * 78)
    print("2. LONG VS. SHORT")
    print("=" * 78)
    for direction, g in trades.groupby("direction"):
        s = trade_stats(g)
        print(f"  {direction:<6} n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}")

    # =========================================================================
    # 3. Entry delay (bars from window close to fill) vs. outcome
    # =========================================================================
    print("\n" + "=" * 78)
    print("3. ENTRY DELAY (bars from window close to breakout fill) VS. OUTCOME")
    print("=" * 78)
    t = trades.copy()
    t["delay_bars"] = ((t["entry_time"] - t["window_end"]).dt.total_seconds() / 900).round().astype(int)
    bins = [0, 1, 2, 4, 8, 100]
    labels = ["0 (immediate)", "1", "2-3", "4-7", "8+"]
    t["delay_bucket"] = pd.cut(t["delay_bars"], bins=bins, labels=labels, right=False)
    for bucket, g in t.groupby("delay_bucket", observed=True):
        s = trade_stats(g)
        print(f"  delay={str(bucket):<15} n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}")

    # =========================================================================
    # 4. MFE analysis of stopped-out trades
    # =========================================================================
    print("\n" + "=" * 78)
    print("4. MAX-FAVORABLE-EXCURSION (MFE) OF STOPPED-OUT TRADES")
    print("=" * 78)
    stopped = trades[trades["exit_reason"] == "stop"].copy()
    print(f"Computing MFE for {len(stopped)} stopped-out trades (re-slicing M15 bars)...")
    stopped["mfe_r"] = compute_mfe(df, stopped)
    print(f"\nMFE distribution (in R-multiples, where the stop is exactly -1R):")
    print(stopped["mfe_r"].describe(percentiles=[0.25, 0.5, 0.75, 0.9]).to_string())

    print("\nShare of stopped-out trades that reached at least X R before reversing:")
    for threshold in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        share = (stopped["mfe_r"] >= threshold).mean()
        print(f"  >= {threshold:>4.2f}R: {share:.1%}")

    # Cross-check: same MFE stat for WINNING trades, as a sanity baseline
    won = trades[trades["return_pct"] > 0].copy()
    won["mfe_r"] = compute_mfe(df, won)
    print(f"\nFor comparison, MFE of WINNING trades (n={len(won)}):")
    print(won["mfe_r"].describe(percentiles=[0.25, 0.5, 0.75, 0.9]).to_string())


if __name__ == "__main__":
    main()
