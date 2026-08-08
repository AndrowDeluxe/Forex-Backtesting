"""Research script: session-window diagnosis for the Gold Asian-Range
Breakout, motivated by Iwatsubo, Watkins & Xu (2017), "Intraday Seasonality
in Efficiency, Liquidity, Volatility and Volume: Platinum and Gold Futures
in Tokyo and New York" (TOCOM vs. COMEX, 1-min data, Sep 2014-Mar 2015).

Their core finding: the Tokyo session in gold/platinum is dominated by
LIQUIDITY trading (volume/volatility high right at the Tokyo open, then
flat/quiet), while the New York session shows evidence of both liquidity
AND INFORMED trading (efficiency - measured via a variance-ratio test -
is comparatively high at the NY open and degrades through the session,
the opposite pattern from Tokyo/London).

This is NOT a new filter or signal - it's a diagnostic check of the
EXISTING production session parameters (RangeStart=21:00, RangeEnd=01:00,
ExitTime=11:00, all NY local - see Gold_Asian_Breakout_Strategy.txt) against
that story: does the range get built during what looks like a liquidity-
driven/quiet window on OUR OWN, current Dukascopy data (not just trust
their stale, 7-month 2014-15 TOCOM/COMEX sample), and does the position get
held into what looks like the more active/informed NY window?

Two parts:
1. Descriptive hour-of-NY-day intraday activity profile (mean |M15 log
   return| and mean bar range as realized-volatility/liquidity proxies -
   we don't have tick-level order-book data, so a true Lo-MacKinlay
   variance-ratio "efficiency" measure per Iwatsubo isn't reproducible
   here; this is a deliberately simpler stand-in, disclosed as such).
   Current RangeStart/RangeEnd/ExitTime are annotated on the profile.
2. A modest ExitTime-only sensitivity sweep (RangeStart/RangeEnd held
   fixed - changing those would alter which bars build the range itself,
   a bigger structural change than this quick diagnostic is scoped for),
   full production filter stack applied (ADX<15 + SMA200 trend-bias +
   entry-delay<=3 + Silver-5-day-alignment), IS/OOS split at 2021-01-01.
   A promising alternative here would still need the fuller walk-forward
   treatment (asian_range_breakout/walkforward.py) before being adopted -
   this sweep only checks whether 11:00 looks well- or poorly-placed,
   it doesn't itself certify a change.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
)
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"

RANGE_START, RANGE_END, CURRENT_EXIT = "21:00", "01:00", "11:00"
EXIT_SWEEP = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}  CAGR={stats.get('cagr', float('nan')):+.2%}"


def build_production_trades(df: pd.DataFrame, daily_close_gold: pd.Series, daily_close_silver: pd.Series, exit_time: str) -> pd.DataFrame:
    trades = simulate_asian_breakout(df, range_start=RANGE_START, range_end=RANGE_END, exit_time=exit_time)
    trades = apply_adx_filter(trades, adx_min=15)
    trades = apply_trend_bias_filter(trades, daily_close_gold, sma_window=200)
    trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    trades = apply_silver_alignment_filter(trades, daily_close_silver, window=5)
    return trades


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()

    print(f"Fetching SILVER M15 {START} -> {END} ...")
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    # =========================================================================
    # 1. Descriptive hour-of-NY-day activity profile
    # =========================================================================
    print("\n" + "=" * 78)
    print("1. HOUR-OF-DAY ACTIVITY PROFILE (NY local time, full 2016-2026 sample)")
    print("=" * 78)
    print(
        "Proxies (no tick data available, so not a true Lo-MacKinlay variance-ratio\n"
        "'efficiency' measure like Iwatsubo's - disclosed simplification):\n"
        "  mean_abs_ret = mean |log return| per M15 bar (realized-volatility proxy)\n"
        "  mean_range   = mean (high-low)/close per M15 bar (intrabar range proxy)\n"
    )
    log_ret = np.log(df["close"]).diff()
    bar_range = (df["high"] - df["low"]) / df["close"]
    hourly = pd.DataFrame({"log_ret": log_ret, "bar_range": bar_range}, index=df.index)
    hourly["hour"] = hourly.index.hour
    profile = hourly.groupby("hour").agg(
        mean_abs_ret=("log_ret", lambda s: s.abs().mean()),
        mean_range=("bar_range", "mean"),
        n_bars=("log_ret", "count"),
    )
    profile["mean_abs_ret_bps"] = profile["mean_abs_ret"] * 1e4
    profile["mean_range_bps"] = profile["mean_range"] * 1e4

    range_start_h, range_end_h, exit_h = int(RANGE_START[:2]), int(RANGE_END[:2]), int(CURRENT_EXIT[:2])
    markers = []
    for h in profile.index:
        tag = []
        if h == range_start_h:
            tag.append("<- RangeStart")
        if h == range_end_h:
            tag.append("<- RangeEnd (breakout armed)")
        if h == exit_h:
            tag.append("<- ExitTime")
        markers.append(" ".join(tag))
    profile["marker"] = markers

    print(profile[["n_bars", "mean_abs_ret_bps", "mean_range_bps", "marker"]].to_string())

    quiet_hours = profile["mean_abs_ret_bps"].nsmallest(4).index.tolist()
    active_hours = profile["mean_abs_ret_bps"].nlargest(4).index.tolist()
    print(f"\nQuietest 4 hours (NY):  {sorted(quiet_hours)}")
    print(f"Most active 4 hours (NY): {sorted(active_hours)}")
    print(
        "Iwatsubo's story predicts: range-building window should sit in the quiet set,\n"
        "the held-through-exit window should sit in (or run into) the active set."
    )

    # =========================================================================
    # 2. ExitTime sensitivity sweep (production filter stack fixed)
    # =========================================================================
    print("\n" + "=" * 78)
    print("2. EXIT-TIME SENSITIVITY SWEEP (full production filter stack, full period)")
    print("=" * 78)
    print("ADX<15 + SMA200 trend-bias + entry-delay<=3 + Silver-5d-alignment held fixed.\n")
    rows = []
    for et in EXIT_SWEEP:
        trades = build_production_trades(df, daily_close_gold, daily_close_silver, et)
        s = trade_stats(trades)
        rows.append({"exit_time": et, **s})
        marker = "  <-- CURRENT PRODUCTION" if et == CURRENT_EXIT else ""
        print(f"{et}  {fmt(s)}{marker}")

    sweep = pd.DataFrame(rows).set_index("exit_time")

    # =========================================================================
    # 3. IS/OOS breakdown at current (11:00) vs. the sweep's best alternative
    # =========================================================================
    best_alt = sweep.drop(index=CURRENT_EXIT)["profit_factor"].idxmax()
    print("\n" + "=" * 78)
    print(f"3. IS/OOS BREAKDOWN -- current ({CURRENT_EXIT}) vs. best alternative from sweep ({best_alt})")
    print("=" * 78)
    for et, label in [(CURRENT_EXIT, "current"), (best_alt, "best-alt")]:
        trades = build_production_trades(df, daily_close_gold, daily_close_silver, et)
        is_trades = trades[trades["entry_time"] < SPLIT]
        oos_trades = trades[trades["entry_time"] >= SPLIT]
        print(f"\n  ExitTime={et} ({label})")
        print(f"    Full: {fmt(trade_stats(trades))}")
        print(f"    IS  : {fmt(trade_stats(is_trades))}")
        print(f"    OOS : {fmt(trade_stats(oos_trades))}")

    print(
        "\nNote: this is a screening sweep, not a walk-forward validation - if an\n"
        "alternative exit time looks materially better here, it still needs the\n"
        "expanding-window walk-forward treatment (walkforward.py pattern) before\n"
        "being trusted as a genuine, forward-usable change rather than in-sample luck."
    )


if __name__ == "__main__":
    main()
