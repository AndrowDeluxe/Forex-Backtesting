"""Research script: the two remaining bond_yield_indicator-derived candidate
filters (Corwin-Schultz FX/Gold liquidity, FOMC event-window), tested against
the Gold Asian-Range Breakout's FULL production stack (ADX + SMA200 trend-
bias + entry-delay<=3 + Silver-5d-alignment) - not just the raw or ADX-only
population, since the decision this script actually informs is "should this
become production filter #5", which is an incremental question on top of
everything already kept.

Same statistical bar as the existing production filters (research_gold_
filter_randomization_test.py): a plain PF/WR/IS-OOS read is NOT enough on
this strategy any more - 2 of the 4 current production filters already
turned out to not clearly beat a structure-preserving (dwell-preserving)
randomization null (Patel et al.), meaning their specific keep/drop pattern
isn't obviously more informative than an arbitrary same-footprint
placement. With ~9 filters already tried on the same fixed 2016-2026 window
before this script, a new candidate only counts if it clears that same null,
not just a headline PF number - see asian_range_breakout/randomization.py
for the exact methodology.

1. Corwin-Schultz liquidity gate: keep trades where GOLD's own prior-day
   estimated bid-ask spread is in the bottom two-thirds (normal-to-good
   liquidity), same "spike"-style tertile-threshold convention as the
   existing VIX-change filter test.
2. FOMC 3-day event-window: tested in BOTH directions (avoid vs. prefer),
   since the source paper's own finding ("out-of-window yield changes are
   transitory") argues for preferring breakouts inside the window, while
   ordinary news-risk intuition argues for avoiding it - no reason to
   privilege one over the other without a fair test of both. ECB/BoE/BoJ/
   BoC/SNB/RBA are not tested here - FOMC is the direct macro driver for a
   USD-denominated asset like Gold, the other 6 banks' calendars in this
   repo also stop at 2024 (see bond_yield_indicator/calendar.py).

The randomization test alone only checks in-sample structural specificity
(is the keep/drop pattern better than an arbitrary same-footprint one on
THIS 10.5y sample) - it does not check whether the filter would have been
usable in real time. Whichever candidate clears the randomization null also
gets the walk-forward check the 4 existing production filters were held to
(asian_range_breakout/walkforward.py): expanding-window, re-confirm the
filter on train-only data each year, apply only if confirmed - a different,
complementary question (out-of-sample persistence)."""

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
    attach_series_level,
)
from asian_range_breakout.randomization import dwell_preserving_test
from asian_range_breakout.walkforward import run_liquidity_filter_walk_forward
from bond_yield_indicator.calendar import event_window_dummy
from bond_yield_indicator.friction import fetch_fx_friction
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
N_SHUFFLES = 1000


def profit_factor(trades: pd.DataFrame) -> float:
    return trade_stats(trades)["profit_factor"]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def report_randomization(name: str, result: dict):
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
    gold_m15 = fetch_gold_m15(START, END)
    daily_close_gold = gold_m15["close"].tz_localize(None).resample("D").last().dropna()

    print(f"Fetching SILVER M15 {START} -> {END} ...")
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    raw_trades = simulate_asian_breakout(gold_m15).sort_values("entry_time").reset_index(drop=True)
    stack = apply_adx_filter(raw_trades, adx_min=15)
    stack = apply_trend_bias_filter(stack, daily_close_gold, sma_window=200)
    stack = apply_entry_delay_filter(stack, max_delay_bars=3)
    stack = apply_silver_alignment_filter(stack, daily_close_silver, window=5)
    stack = stack.sort_values("entry_time").reset_index(drop=True)
    print(f"\nFull production stack (ADX+Trend+Delay+Silver): {len(stack)} / {len(raw_trades)} raw trades kept.")

    # =========================================================================
    # 1. Corwin-Schultz GOLD liquidity gate
    # =========================================================================
    print("\n" + "=" * 78)
    print("1. CORWIN-SCHULTZ GOLD-LIQUIDITY GATE")
    print("=" * 78)
    print("Fetching Gold D1 Corwin-Schultz friction proxy ...")
    friction = fetch_fx_friction("GOLD", START, END)
    thresh = friction.quantile(2 / 3)
    print(f"Bottom-two-thirds threshold (normal-to-good liquidity): {thresh:.4%}")

    t_liq = attach_series_level(stack, friction, "friction_prior").dropna(subset=["friction_prior"])
    mask_liquid = (t_liq["friction_prior"] <= thresh).reset_index(drop=True)
    t_liq = t_liq.reset_index(drop=True)

    liquid = t_liq[mask_liquid]
    illiquid = t_liq[~mask_liquid]
    is_p, oos_p = t_liq["entry_time"] < SPLIT, t_liq["entry_time"] >= SPLIT
    print(f"{'':<12}{'Normal/good liquidity':<28}{'Poor liquidity':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(liquid)):<28}{fmt(trade_stats(illiquid)):<28}")
    print(f"{'IS':<12}{fmt(trade_stats(liquid[is_p[mask_liquid]])):<28}{fmt(trade_stats(illiquid[is_p[~mask_liquid]])):<28}")
    print(f"{'OOS':<12}{fmt(trade_stats(liquid[oos_p[mask_liquid]])):<28}{fmt(trade_stats(illiquid[oos_p[~mask_liquid]])):<28}")

    result_liq = dwell_preserving_test(t_liq, mask_liquid, profit_factor, n_shuffles=N_SHUFFLES, seed=11)
    report_randomization("Keep normal/good-liquidity trades  (population: full production stack)", result_liq)

    print("\nWalk-forward (expanding window, train-only confirmation each test year):")
    wf = run_liquidity_filter_walk_forward(t_liq, start_test_year=2019, end_test_year=2026, min_train_trades=100)
    if wf.empty:
        print("  not enough trades for any test year at min_train_trades=100.")
    else:
        print(wf.to_string(index=False))
        n_confirmed = int(wf["filter_confirmed_on_train"].sum())
        total_wf_trades = int(wf["n_trades_walkforward"].sum())
        print(
            f"  Confirmed on train-only data in {n_confirmed}/{len(wf)} test years "
            f"({total_wf_trades} total walk-forward trades). "
            f"Mean unfiltered PF/year={wf['pf_unfiltered'].mean():.3f}, "
            f"mean walk-forward PF/year={wf['pf_walkforward'].mean():.3f}."
        )

    # =========================================================================
    # 2. FOMC 3-day event window (both directions)
    # =========================================================================
    print("\n" + "=" * 78)
    print("2. FOMC 3-DAY EVENT WINDOW (avoid vs. prefer)")
    print("=" * 78)
    entry_dates = stack["entry_time"].dt.tz_localize(None).dt.normalize()
    date_grid = pd.date_range(entry_dates.min() - pd.Timedelta(days=2), entry_dates.max() + pd.Timedelta(days=2), freq="D")
    event_flag = event_window_dummy("FOMC", date_grid, window_days=1)
    in_event = entry_dates.map(event_flag).fillna(0).astype(bool).reset_index(drop=True)
    t_evt = stack.reset_index(drop=True)

    inside = t_evt[in_event]
    outside = t_evt[~in_event]
    print(f"{len(inside)} trades inside a FOMC 3-day window, {len(outside)} outside.")
    print(f"{'':<12}{'Inside window':<28}{'Outside window':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(inside)):<28}{fmt(trade_stats(outside)):<28}")
    is_p2, oos_p2 = t_evt["entry_time"] < SPLIT, t_evt["entry_time"] >= SPLIT
    print(f"{'IS':<12}{fmt(trade_stats(inside[is_p2[in_event]])):<28}{fmt(trade_stats(outside[is_p2[~in_event]])):<28}")
    print(f"{'OOS':<12}{fmt(trade_stats(inside[oos_p2[in_event]])):<28}{fmt(trade_stats(outside[oos_p2[~in_event]])):<28}")

    result_prefer = dwell_preserving_test(t_evt, in_event, profit_factor, n_shuffles=N_SHUFFLES, seed=12)
    report_randomization("Prefer inside window  (population: full production stack)", result_prefer)
    result_avoid = dwell_preserving_test(t_evt, ~in_event, profit_factor, n_shuffles=N_SHUFFLES, seed=13)
    report_randomization("Avoid (keep outside window)  (population: full production stack)", result_avoid)

    print(
        "\nReading guide (same as research_gold_filter_randomization_test.py): p < 0.05 under "
        "BOTH rotation and run_permutation = the filter's actual keep/drop pattern beats the "
        "large majority of same-footprint alternative placements -> plausible genuine selection "
        "skill. High p-value = a same-footprint filter with no relation to the indicator would "
        "typically have looked about as good -> not a real edge, just this exposure shape."
    )


if __name__ == "__main__":
    main()
