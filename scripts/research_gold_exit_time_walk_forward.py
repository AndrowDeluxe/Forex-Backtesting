"""Follow-up to the Iwatsubo session-diagnostic screening sweep
(scripts/research_gold_session_iwatsubo_diagnosis.py), which flagged
ExitTime=10:00 as a mild candidate vs. the production 11:00 (marginally
better IS and OOS point estimates, but explicitly not walk-forward
validated). This applies the actual expanding-window walk-forward
treatment that finding was flagged as needing, before it can be considered
for production - same discipline as the three existing ADX/trend-bias/
delay walk-forward checks (asian_range_breakout/walkforward.py).
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
)
from asian_range_breakout.walkforward import run_exit_time_walk_forward
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
DEFAULT_EXIT = "11:00"
CANDIDATES = ["09:00", "10:00", "11:00", "12:00"]


def build_trades(df, daily_close_gold, daily_close_silver, exit_time):
    trades = simulate_asian_breakout(df, exit_time=exit_time)
    trades = apply_adx_filter(trades, adx_min=15)
    trades = apply_trend_bias_filter(trades, daily_close_gold, sma_window=200)
    trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    trades = apply_silver_alignment_filter(trades, daily_close_silver, window=5)
    return trades.sort_values("entry_time").reset_index(drop=True)


def main():
    print(f"Fetching GOLD/SILVER M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    trades_by_exit = {et: build_trades(df, daily_close_gold, daily_close_silver, et) for et in CANDIDATES}

    print("\nFull-period stats per candidate (production filter stack):")
    for et, t in trades_by_exit.items():
        s = trade_stats(t)
        marker = "  <-- current production" if et == DEFAULT_EXIT else ""
        print(f"  {et}  n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}{marker}")

    print("\n" + "=" * 78)
    print("EXPANDING-WINDOW WALK-FORWARD on ExitTime choice")
    print("=" * 78)
    wf = run_exit_time_walk_forward(
        trades_by_exit, default_exit=DEFAULT_EXIT, start_test_year=2019, end_test_year=2026, min_train_trades=30
    )
    print(wf.to_string(index=False))

    valid = wf.dropna(subset=["pf_walkforward"])
    n_beats_default = (valid["pf_walkforward"] > valid["pf_default"]).sum()
    print(f"\nYears where walk-forward-chosen exit beat the default (11:00): {n_beats_default}/{len(valid)}")
    print(
        "If this isn't a clear majority with a meaningfully higher aggregate PF, treat 11:00 as still\n"
        "well-calibrated - a marginal in-sample screening edge that doesn't hold up walk-forward-style\n"
        "isn't grounds to touch production, per this repo's own overfitting-avoidance discipline."
    )


if __name__ == "__main__":
    main()
