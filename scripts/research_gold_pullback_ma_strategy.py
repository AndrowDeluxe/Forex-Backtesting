"""Research script: MA-pullback strategy on Gold, per Beluska & Vojtko's
multi-asset pullback template (200-day-MA uptrend filter + N-consecutive-
down-day trigger + 1-day hold; paper tests 6 ETFs incl. GLD with a dynamic
equal-weight overlay across simultaneously active signals - dropped here
since we only trade one instrument).

This is a genuinely NEW, independent candidate strategy (not a filter on
top of the Asian-Range Breakout) - own backend package (gold_pullback_ma/),
own signal, own entry/exit, real Dukascopy Gold daily bars (resampled from
the same M15 source as asian_range_breakout). Phase 5 (combining this with
existing ASB building blocks, if it survives) is explicitly out of scope
here.

Caveat up front: the exact headline N the paper reports isn't reproduced
from memory here (paper text isn't available in this session anymore) -
this replicates the STRATEGY TEMPLATE (200MA + N-day pullback + 1-day
hold) with our own parameter sweep across N and MA window, rather than a
literal single-parameter replication.

Rigor pattern matches scripts/research_gold_trend_bias_seasonality.py:
sweep -> IS/OOS breakdown at the standout combo -> outlier-sensitivity
check -> expanding-window walk-forward.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_pullback_ma.data import fetch_gold_daily_ohlc
from gold_pullback_ma.engine import simulate_pullback
from gold_pullback_ma.walkforward import run_pullback_walk_forward
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01")

N_CANDIDATES = [1, 2, 3, 4, 5]
MA_CANDIDATES = [150, 200, 250]
COST_BPS = 5.0


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}  avg_ret={stats['avg_return_pct']:+.3%}"


def main():
    print(f"Fetching GOLD daily OHLC {START} -> {END} ...")
    daily = fetch_gold_daily_ohlc(START, END)
    print(f"{len(daily)} daily bars")

    # =========================================================================
    # 1. Parameter sweep: n_down_days x ma_window, full period
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"1. PARAMETER SWEEP (full period, cost_bps={COST_BPS})")
    print("=" * 78)
    rows = []
    for ma_window in MA_CANDIDATES:
        for n in N_CANDIDATES:
            trades = simulate_pullback(daily, ma_window=ma_window, n_down_days=n, cost_bps=COST_BPS)
            s = trade_stats(trades)
            rows.append({"ma_window": ma_window, "n_down_days": n, **s})
            print(f"  MA={ma_window:>3}  N={n}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= 30]
    if eligible.empty:
        print("\nNo combo reaches 30 trades - stopping, material too thin to draw conclusions.")
        return
    best = eligible.loc[eligible["profit_factor"].idxmax()]
    ma_primary, n_primary = int(best["ma_window"]), int(best["n_down_days"])
    print(f"\nStandout combo (highest PF, n>=30): MA={ma_primary}, N={n_primary}  {fmt(trade_stats(simulate_pullback(daily, ma_primary, n_primary, COST_BPS)))}")

    # =========================================================================
    # 2. IS/OOS breakdown at the standout combo
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"2. IS/OOS BREAKDOWN -- MA={ma_primary}, N={n_primary}  (split={SPLIT.date()})")
    print("=" * 78)
    trades = simulate_pullback(daily, ma_window=ma_primary, n_down_days=n_primary, cost_bps=COST_BPS)
    is_trades = trades[trades["entry_time"] < SPLIT]
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    print(f"  Full: {fmt(trade_stats(trades))}")
    print(f"  IS  : {fmt(trade_stats(is_trades))}")
    print(f"  OOS : {fmt(trade_stats(oos_trades))}")

    # =========================================================================
    # 3. Outlier-sensitivity check
    # =========================================================================
    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK (drop single best trade)")
    print("=" * 78)
    sorted_ret = trades["return_pct"].sort_values(ascending=False)
    without_best = trades.drop(index=sorted_ret.index[0])
    s_full = trade_stats(trades)
    s_wo = trade_stats(without_best)
    print(f"  Full PF:          {s_full['profit_factor']:.3f}")
    print(f"  Without best trade PF: {s_wo['profit_factor']:.3f}")
    if s_wo["profit_factor"] <= 1.0:
        print("  -> PF collapses to <=1.0 without the single best trade: edge is outlier-driven, not robust.")
    else:
        print("  -> PF stays above 1.0 without the single best trade.")

    # =========================================================================
    # 4. Expanding-window walk-forward on N (MA window held fixed at primary)
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"4. EXPANDING-WINDOW WALK-FORWARD on n_down_days (MA={ma_primary} fixed)")
    print("=" * 78)
    wf = run_pullback_walk_forward(
        daily, ma_window=ma_primary, n_candidates=N_CANDIDATES,
        start_test_year=2019, end_test_year=2026, min_train_trades=20, cost_bps=COST_BPS,
    )
    print(wf.to_string(index=False))

    print(
        "\nNote: chosen_n is picked purely from strictly-prior years' train PF each year, then\n"
        "applied forward untouched - this is the closest thing to a genuinely out-of-sample\n"
        "read on this parameter choice available with a single ~10-year history."
    )


if __name__ == "__main__":
    main()
