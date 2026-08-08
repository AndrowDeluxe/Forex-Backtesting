"""Follow-up to the Beluska & Vojtko pullback strategy, which found no
robust standalone edge (scripts/research_gold_pullback_ma_strategy.py).
The strategy failed, but its two BUILDING BLOCKS - Gold's own consecutive
daily down-day streak, and Gold's % distance from its 200-day SMA - are
still candidate CONTEXT SIGNALS that might carry incremental filtering
value for the Asian-Range Breakout even though they didn't work as a
standalone buy-the-dip signal. Tests both, layered on top of the full
production filter stack (ADX+Trend+Delay+Silver), same no-lookahead
prior-day alignment used for every other cross-signal filter in this repo
(filters.py::attach_series_level).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
    attach_series_level,
)
from combined_strategy.data import fetch_timeframe
from gold_pullback_ma.engine import _consecutive_down_days
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD/SILVER M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    production_trades = simulate_asian_breakout(df)
    production_trades = apply_adx_filter(production_trades, adx_min=15)
    production_trades = apply_trend_bias_filter(production_trades, daily_close_gold, sma_window=200)
    production_trades = apply_entry_delay_filter(production_trades, max_delay_bars=3)
    production_trades = apply_silver_alignment_filter(production_trades, daily_close_silver, window=5)
    production_trades = production_trades.sort_values("entry_time").reset_index(drop=True)
    print(f"\nProduction stack (before any new filter): {fmt(trade_stats(production_trades))}")

    # =========================================================================
    # 1. Consecutive down-day streak (Beluska/Vojtko's pullback trigger)
    # =========================================================================
    consec_down = _consecutive_down_days(daily_close_gold)
    t1 = attach_series_level(production_trades, consec_down, "consec_down_prior")
    print("\n" + "=" * 78)
    print("1. Bucketed by Gold's own consecutive-down-day streak (prior day)")
    print("=" * 78)
    t1["bucket"] = pd.cut(t1["consec_down_prior"], bins=[-1, 0, 1, 2, 99], labels=["0", "1", "2", "3+"])
    for b, g in t1.groupby("bucket", observed=True):
        print(f"  streak={b:>2}  {fmt(trade_stats(g))}")

    # =========================================================================
    # 2. % distance from 200-day SMA (trend STRENGTH, not just direction -
    #    trend-bias filter already tests direction; this tests magnitude)
    # =========================================================================
    sma200 = daily_close_gold.rolling(200).mean()
    pct_from_ma = (daily_close_gold - sma200) / sma200 * 100
    t2 = attach_series_level(production_trades, pct_from_ma, "pct_from_ma200_prior")
    t2 = t2.dropna(subset=["pct_from_ma200_prior"])
    print("\n" + "=" * 78)
    print("2. Bucketed by Gold's % distance from its own 200-day SMA (prior day, terciles)")
    print("=" * 78)
    try:
        t2["bucket"] = pd.qcut(t2["pct_from_ma200_prior"].abs(), 3, labels=["near (weak trend)", "mid", "far (strong trend)"])
        for b, g in t2.groupby("bucket", observed=True):
            print(f"  {b:<20} {fmt(trade_stats(g))}")
    except ValueError as e:
        print(f"  (qcut failed: {e})")

    print(
        "\nReading: if PF rises monotonically with streak length or with |distance from MA|, that's a\n"
        "plausible new filter worth an IS/OOS + walk-forward check before adopting. If it's flat or\n"
        "non-monotonic, the building block carries no usable incremental information for the ASB\n"
        "beyond what ADX/Trend/Delay/Silver already capture, even though it came from a real paper."
    )


if __name__ == "__main__":
    main()
