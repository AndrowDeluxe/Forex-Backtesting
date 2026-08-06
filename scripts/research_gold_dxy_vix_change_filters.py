"""Research script: two "151 Trading Strategies" cross-asset-context ideas
(paper151 Gold tab, 2026-08-06) tested against the Gold Asian-Range Breakout
-- the one strategy in this repo with an actual edge, so any new filter is
judged against the ADX-filtered production config, not the raw baseline.

1. DXY-alignment filter: Gold is USD-denominated, so a trending dollar is a
   structural head-/tailwind independent of Gold's own chart. Hypothesis:
   long trades taken while the dollar (DXY) has been FALLING, and short
   trades taken while it has been RISING, should hold up better than trades
   fighting that backdrop.
2. VIX-change-rate filter: the existing VIX-LEVEL filter (asian_range_
   breakout/filters.py::apply_vix_filter) was already tested and found to be
   noise (see app_pages/asian_range_breakout.py). The paper's "spike, not
   level" framing suggests testing the RATE OF CHANGE instead - does a
   fresh vol spike (not just "VIX is high") correlate with stronger/weaker
   breakout continuation?

Same discipline as every other filter test in this repo: full period, IS/OOS
split (2021-01-01), and a window-length sensitivity sweep before trusting any
single number - a filter that only "works" at one arbitrary window is noise,
not a finding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.dxy import fetch_dxy_daily
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter, attach_series_change
from asian_range_breakout.vix import fetch_vix_daily
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
CTX_START = "2015-06-01"  # earlier start so change-rate windows have run-up data from day 1
SPLIT = "2021-01-01"
WINDOWS = [3, 5, 10, 20]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    gold = fetch_gold_m15(START, END)
    trades_all = simulate_asian_breakout(gold)
    trades = apply_adx_filter(trades_all, adx_min=15)
    print(f"{len(trades_all)} raw trades, {len(trades)} after the production ADX<15 filter.")

    print(f"\nFetching DXY {CTX_START} -> {END} ...")
    dxy_daily = fetch_dxy_daily(CTX_START, END)
    print(f"Fetching VIX {CTX_START} -> {END} ...")
    vix_daily = fetch_vix_daily(CTX_START, END)

    is_long = trades["direction"] == "long"

    # =========================================================================
    # 1. DXY-alignment: window sensitivity sweep (full period only)
    # =========================================================================
    print("\n" + "=" * 78)
    print("1. DXY-ALIGNMENT -- window sensitivity sweep (full period)")
    print("=" * 78)
    print("Aligned  = long while DXY falling, short while DXY rising (dollar tailwind)")
    print("Misaligned = long while DXY rising, short while DXY falling (fighting the dollar)")
    print(f"{'window':>6}  {'aligned':<28}  {'misaligned':<28}  {'neutral(chg==0)':<15}")
    for w in WINDOWS:
        t = attach_series_change(trades, dxy_daily, "dxy_chg", window=w)
        dxy_up = t["dxy_chg"] > 0
        dxy_down = t["dxy_chg"] < 0
        aligned_mask = (is_long & dxy_down) | (~is_long & dxy_up)
        misaligned_mask = (is_long & dxy_up) | (~is_long & dxy_down)
        aligned = trade_stats(t[aligned_mask])
        misaligned = trade_stats(t[misaligned_mask])
        neutral_n = int((t["dxy_chg"] == 0).sum())
        print(f"{w:>6}  {fmt(aligned):<28}  {fmt(misaligned):<28}  {neutral_n:<15}")

    # =========================================================================
    # 2. DXY-alignment: full IS/OOS breakdown at window=5
    # =========================================================================
    W_DXY = 5
    print("\n" + "=" * 78)
    print(f"2. DXY-ALIGNMENT -- IS/OOS breakdown at window={W_DXY}")
    print("=" * 78)
    t5 = attach_series_change(trades, dxy_daily, "dxy_chg", window=W_DXY)
    dxy_up = t5["dxy_chg"] > 0
    dxy_down = t5["dxy_chg"] < 0
    aligned_mask = (is_long & dxy_down) | (~is_long & dxy_up)
    misaligned_mask = (is_long & dxy_up) | (~is_long & dxy_down)

    is_period = t5["entry_time"] < SPLIT
    oos_period = t5["entry_time"] >= SPLIT

    print(f"{'':<12}{'Aligned':<28}{'Misaligned':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(t5[aligned_mask])):<28}{fmt(trade_stats(t5[misaligned_mask])):<28}")
    print(
        f"{'IS':<12}{fmt(trade_stats(t5[aligned_mask & is_period])):<28}"
        f"{fmt(trade_stats(t5[misaligned_mask & is_period])):<28}"
    )
    print(
        f"{'OOS':<12}{fmt(trade_stats(t5[aligned_mask & oos_period])):<28}"
        f"{fmt(trade_stats(t5[misaligned_mask & oos_period])):<28}"
    )

    # =========================================================================
    # 3. VIX-change-rate ("spike"): window sensitivity sweep (full period)
    # =========================================================================
    print("\n" + "=" * 78)
    print("3. VIX-CHANGE-RATE ('spike') -- window sensitivity sweep (full period)")
    print("=" * 78)
    print("Spike = top tertile of window-day VIX %-change (freshest third of vol run-ups)")
    print(f"{'window':>6}  {'spike':<28}  {'no_spike':<28}")
    for w in WINDOWS:
        t = attach_series_change(trades, vix_daily, "vix_chg", window=w)
        t = t.dropna(subset=["vix_chg"])
        thresh = t["vix_chg"].quantile(2 / 3)
        spike_mask = t["vix_chg"] >= thresh
        no_spike_mask = ~spike_mask
        print(
            f"{w:>6}  {fmt(trade_stats(t[spike_mask])):<28}  {fmt(trade_stats(t[no_spike_mask])):<28}"
            f"  (threshold: {thresh:+.1f}%)"
        )

    # =========================================================================
    # 4. VIX-change-rate: full IS/OOS breakdown at window=5
    # =========================================================================
    W_VIX = 5
    print("\n" + "=" * 78)
    print(f"4. VIX-CHANGE-RATE ('spike') -- IS/OOS breakdown at window={W_VIX}")
    print("=" * 78)
    tv = attach_series_change(trades, vix_daily, "vix_chg", window=W_VIX).dropna(subset=["vix_chg"])
    thresh_full = tv["vix_chg"].quantile(2 / 3)
    spike_mask = tv["vix_chg"] >= thresh_full
    is_period_v = tv["entry_time"] < SPLIT
    oos_period_v = tv["entry_time"] >= SPLIT

    print(f"Full-period spike threshold (top tertile): {thresh_full:+.1f}%")
    print(f"{'':<12}{'Spike':<28}{'No spike':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(tv[spike_mask])):<28}{fmt(trade_stats(tv[~spike_mask])):<28}")
    print(
        f"{'IS':<12}{fmt(trade_stats(tv[spike_mask & is_period_v])):<28}"
        f"{fmt(trade_stats(tv[~spike_mask & is_period_v])):<28}"
    )
    print(
        f"{'OOS':<12}{fmt(trade_stats(tv[spike_mask & oos_period_v])):<28}"
        f"{fmt(trade_stats(tv[~spike_mask & oos_period_v])):<28}"
    )


if __name__ == "__main__":
    main()
