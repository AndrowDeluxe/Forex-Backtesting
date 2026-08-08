"""Follow-up to the Patel structure-preserving-randomization test
(scripts/research_gold_filter_randomization_test.py), which found that two
of the four production filters (SMA200 trend-bias, entry-delay<=3) don't
clearly clear the dwell-preserving null (p~0.16-0.23) - i.e. their specific
keep/drop pattern isn't clearly distinguishable from an arbitrary
same-footprint placement, even though both separately passed the (different
question) walk-forward persistence check.

This runs a plain ablation: every filter-stack combination that includes
ADX (the baseline regime filter, always kept) with Trend-Bias/Delay/Silver
each independently in or out, full-period + IS/OOS for each - to see
concretely whether dropping the two weak-significance filters actually
costs anything, or whether they're redundant/noise on top of ADX+Silver.
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
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")

COMBOS = [
    ("ADX only", ["ADX"]),
    ("ADX+Trend", ["ADX", "Trend"]),
    ("ADX+Delay", ["ADX", "Delay"]),
    ("ADX+Silver", ["ADX", "Silver"]),
    ("ADX+Trend+Delay", ["ADX", "Trend", "Delay"]),
    ("ADX+Trend+Silver", ["ADX", "Trend", "Silver"]),
    ("ADX+Delay+Silver", ["ADX", "Delay", "Silver"]),
    ("ADX+Trend+Delay+Silver (production)", ["ADX", "Trend", "Delay", "Silver"]),
]


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

    raw_trades = simulate_asian_breakout(df)

    step_funcs = {
        "ADX": lambda t: apply_adx_filter(t, adx_min=15),
        "Trend": lambda t: apply_trend_bias_filter(t, daily_close_gold, sma_window=200),
        "Delay": lambda t: apply_entry_delay_filter(t, max_delay_bars=3),
        "Silver": lambda t: apply_silver_alignment_filter(t, daily_close_silver, window=5),
    }

    print("\n" + "=" * 100)
    print(f"{'Combo':<38}{'Full':<28}{'IS':<28}{'OOS'}")
    print("=" * 100)
    for name, steps in COMBOS:
        trades = raw_trades
        for step in steps:
            trades = step_funcs[step](trades)
        trades = trades.sort_values("entry_time")
        is_t = trades[trades["entry_time"] < SPLIT]
        oos_t = trades[trades["entry_time"] >= SPLIT]
        marker = "  <-- production" if "production" in name else ""
        print(f"{name:<38}{fmt(trade_stats(trades)):<28}{fmt(trade_stats(is_t)):<28}{fmt(trade_stats(oos_t))}{marker}")

    print(
        "\nReading: if ADX+Silver (dropping the two weak-significance filters) matches or beats\n"
        "production on OOS PF with a similar or larger trade count, Trend-Bias/Delay are adding\n"
        "little beyond noise/redundancy despite passing their own walk-forward checks. If production\n"
        "still clearly leads OOS, keep the full stack - walk-forward persistence still outweighs a\n"
        "structural-specificity test that answers a different question."
    )


if __name__ == "__main__":
    main()
