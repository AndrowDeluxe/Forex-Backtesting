"""Research script: Structure-Preserving Randomization Inference (Patel et
al.) applied to the four existing Gold ASB production filters (ADX<15,
SMA200 trend-bias, entry-delay<=3, Silver-5d-alignment).

All four were already walk-forward-validated (asian_range_breakout/
walkforward.py) - this is a different, complementary check: walk-forward
asks "does the filter's edge persist out-of-sample year by year", while
this asks "is the filter's specific keep/drop pattern actually informative,
or would ANY filter with the same footprint (same number of trades kept,
same run-length/dwell structure of on/off stretches) have looked about as
good just because of when those stretches happen to fall relative to
Gold's own drift/vol clustering?" A filter that passes walk-forward but
fails this check would suggest the edge is more about *which slice of the
calendar* gets included than about the indicator itself carrying
information.

Each filter is tested on the population it actually acts on in the
production stack (ADX on the raw trade population; trend-bias on the
ADX-filtered population; delay on the ADX+trend-bias-filtered population;
Silver-alignment on the ADX+trend-bias+delay-filtered population) - i.e.
exactly the incremental question production asks of each filter.
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
    attach_entry_delay,
    attach_silver_alignment,
    attach_trend_bias,
)
from asian_range_breakout.randomization import dwell_preserving_test
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
N_SHUFFLES = 1000


def profit_factor(trades: pd.DataFrame) -> float:
    return trade_stats(trades)["profit_factor"]


def report(name: str, result: dict):
    print(f"\n--- {name} ---")
    print(f"  kept {result['n_kept']} / {result['n_total']} trades   actual PF = {result['actual_metric']:.3f}")
    for method in ("rotation", "run_permutation"):
        r = result[method]
        print(
            f"  [{method:>15}]  null PF mean={r['null_mean']:.3f}  std={r['null_std']:.3f}  "
            f"[p05={r['null_p05']:.3f}, p95={r['null_p95']:.3f}]  "
            f"p-value(null>=actual)={r['p_value']:.3f}  (n_valid={r['n_valid_shuffles']}/{N_SHUFFLES})"
        )


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()

    print(f"Fetching SILVER M15 {START} -> {END} ...")
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    raw_trades = simulate_asian_breakout(df).sort_values("entry_time").reset_index(drop=True)
    print(f"\nRaw (unfiltered) breakout trades: {len(raw_trades)}")

    # --- 1. ADX >= 15 (trending regime), tested against the raw population ---
    mask_adx = (raw_trades["adx_at_entry"] >= 15).reset_index(drop=True)
    result_adx = dwell_preserving_test(raw_trades, mask_adx, profit_factor, n_shuffles=N_SHUFFLES, seed=1)
    report("1. ADX >= 15  (population: raw trades)", result_adx)

    after_adx = apply_adx_filter(raw_trades, adx_min=15).sort_values("entry_time").reset_index(drop=True)

    # --- 2. SMA200 trend-bias, tested against the ADX-filtered population ---
    with_bias = attach_trend_bias(after_adx, daily_close_gold, sma_window=200).sort_values("entry_time").reset_index(drop=True)
    mask_bias = with_bias["aligned"].reset_index(drop=True)
    result_bias = dwell_preserving_test(with_bias, mask_bias, profit_factor, n_shuffles=N_SHUFFLES, seed=2)
    report("2. SMA200 trend-bias  (population: ADX-filtered)", result_bias)

    after_bias = apply_trend_bias_filter(after_adx, daily_close_gold, sma_window=200).sort_values("entry_time").reset_index(drop=True)

    # --- 3. Entry-delay <= 3, tested against the ADX+trend-bias-filtered population ---
    with_delay = attach_entry_delay(after_bias).sort_values("entry_time").reset_index(drop=True)
    mask_delay = (with_delay["delay_bars"] <= 3).reset_index(drop=True)
    result_delay = dwell_preserving_test(with_delay, mask_delay, profit_factor, n_shuffles=N_SHUFFLES, seed=3)
    report("3. Entry-delay <= 3 bars  (population: ADX+trend-bias-filtered)", result_delay)

    after_delay = apply_entry_delay_filter(after_bias, max_delay_bars=3).sort_values("entry_time").reset_index(drop=True)

    # --- 4. Silver-5d-alignment, tested against the ADX+trend-bias+delay-filtered population ---
    with_silver = attach_silver_alignment(after_delay, daily_close_silver, window=5).sort_values("entry_time").reset_index(drop=True)
    mask_silver = with_silver["aligned"].reset_index(drop=True)
    result_silver = dwell_preserving_test(with_silver, mask_silver, profit_factor, n_shuffles=N_SHUFFLES, seed=4)
    report("4. Silver-5d-alignment  (population: ADX+trend-bias+delay-filtered)", result_silver)

    print(
        "\nReading guide: low p-value (e.g. < 0.05) under BOTH methods = the filter's actual\n"
        "keep/drop pattern beats the large majority of same-footprint (same count, same\n"
        "run-length structure) alternative placements -> plausible genuine selection skill.\n"
        "High p-value = a same-footprint filter with no relation to the indicator at all\n"
        "would typically have looked about as good -> the apparent edge is more likely just\n"
        "this exposure shape (which/how-long stretches got included), not the indicator's\n"
        "informational content. This does not replace the walk-forward check - it answers a\n"
        "different question (in-sample structural specificity vs. out-of-sample persistence)."
    )


if __name__ == "__main__":
    main()
