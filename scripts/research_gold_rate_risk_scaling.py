"""Research script: cross-asset rate-momentum RISK-SCALING (not gate) for
Gold Asian-Range-Breakout - first application of the cls_practical.rates
mechanism outside cls_practical itself (2026-09-09, JPM "Cross Asset
Momentum Spillover" paper cross-check, see knowledge/resources/
cross-asset-momentum-spillover.md).

Different test than scripts/research_gold_yield_filter.py (2026-08-11,
already rejected, see knowledge/resources/fx-microstructure.md): that
script tested US-10Y-yield ALIGNMENT as a hard long/short GATE-split and
found a noise pattern. cls_practical's own research found the identical
GATE framing of its rates signal failed too (only 2/18 swept configs beat
baseline, thin samples), while a continuous risk-SCALING multiplier
(bigger positions when the signal is strongly confirmed, unchanged
otherwise - never drops a trade) passed with full IS/OOS + per-year
robustness (5/5 split points). This script applies THAT already-validated
mechanism - compute_daily_rate_risk_multiplier (BUND/USTBOND CFD,
long-end) x compute_frontend_2y_risk_multiplier (DE02Y/US02Y, front-end)
via compute_combined_rate_risk_multiplier - to Gold ASB's own ADX-filtered
production trades, using its EXACT default config (lag=2/1, z>=0.5,
1.75x). No new parameter sweep in this first pass.

Same discipline as every other Gold ASB filter: expanding-window walk-
forward (train-only confirmation per test year,
asian_range_breakout.walkforward.run_rate_scaling_walk_forward) PLUS a
structure-preserving randomization null (asian_range_breakout.
randomization's rotation/run_permutation shufflers, adapted here for a
scaling multiplier instead of a keep/drop mask - see _scaling_metric
below)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter
from asian_range_breakout.randomization import rotation_shuffle, run_permutation_shuffle
from asian_range_breakout.sizing import simulate_equity
from asian_range_breakout.walkforward import _dollar_profit_factor, run_rate_scaling_walk_forward
from cls_practical.data import fetch_2y_yield_daily, fetch_rate_instrument_m5_berlin
from cls_practical.rates import compute_combined_rate_risk_multiplier

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
WF_START_YEAR, WF_END_YEAR = 2021, 2026
RISK_PCT = 0.005
N_SHUFFLES = 1000


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    gold = fetch_gold_m15(START, END)
    trades_all = simulate_asian_breakout(gold)
    trades = apply_adx_filter(trades_all, adx_min=15)
    trades = trades.sort_values("entry_time").reset_index(drop=True)
    print(f"{len(trades_all)} raw trades, {len(trades)} after the production ADX<15 filter.")

    print("\nFetching rate instruments (BUND/USTBOND CFD + DE02Y/US02Y) ...")
    bund = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    de02y = fetch_2y_yield_daily("DE02Y")
    us02y = fetch_2y_yield_daily("US02Y")

    entry_dates = trades["entry_time"].dt.tz_localize(None).dt.date
    direction_by_date = dict(
        zip(entry_dates.to_numpy(), np.where(trades["direction"].to_numpy() == "long", 1, -1))
    )
    direction = pd.Series(direction_by_date)

    combined_mult = compute_combined_rate_risk_multiplier(bund, ustbond, de02y, us02y, direction)
    n_scaled = int((combined_mult > 1.0).sum())
    print(
        f"{len(combined_mult)} trade-date multiplier readings, {n_scaled} scaled "
        f"('grün' on >=1 leg, up to 1.75x*1.75x=3.0625x on both)."
    )

    # =========================================================================
    # 1. Flat vs. scaled, full period + IS/OOS (naive, no walk-forward)
    # =========================================================================
    flat = simulate_equity(trades, risk_pct=RISK_PCT)
    scaled = simulate_equity(trades, risk_pct=RISK_PCT, risk_multiplier=combined_mult)

    def _report(label, sim):
        is_ = sim[sim["entry_time"] < SPLIT]
        oos = sim[sim["entry_time"] >= SPLIT]
        print(
            f"{label:<10} Full: PF={_dollar_profit_factor(sim):.3f}  EndEq=${sim['equity'].iloc[-1]:,.0f}   "
            f"IS: PF={_dollar_profit_factor(is_):.3f}   OOS: PF={_dollar_profit_factor(oos):.3f}"
        )

    print("\n" + "=" * 78)
    print("1. FLAT vs. RATE-SCALED -- full period + IS/OOS (naive, no walk-forward)")
    print("=" * 78)
    _report("Flat", flat)
    _report("Scaled", scaled)

    # =========================================================================
    # 2. Walk-forward (expanding-window, train-only confirmation per year)
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"2. WALK-FORWARD ({WF_START_YEAR}-{WF_END_YEAR})")
    print("=" * 78)
    summary, wf_trades = run_rate_scaling_walk_forward(
        trades, combined_mult, WF_START_YEAR, WF_END_YEAR, risk_pct=RISK_PCT
    )
    print(summary.to_string(index=False))
    if not wf_trades.empty:
        print(
            f"\nWalk-forward stitched: PF={_dollar_profit_factor(wf_trades):.3f}  "
            f"EndEquity=${wf_trades['equity'].iloc[-1]:,.0f}"
        )

    # =========================================================================
    # 3. Structure-preserving randomization null (adapted for scaling)
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"3. RANDOMIZATION ({N_SHUFFLES} shuffles/method) -- is the scaled-day pattern special?")
    print("=" * 78)
    combined_by_date = combined_mult.reindex(entry_dates.to_numpy(), fill_value=1.0)
    is_scaled_mask = (combined_by_date.to_numpy() > 1.0)
    base_level = 1.0
    scaled_level = float(combined_mult[combined_mult > 1.0].mean()) if n_scaled else 1.75
    print(f"scaled_level (mean multiplier on scaled days) = {scaled_level:.3f}, n_scaled={n_scaled}/{len(trades)}")

    def _scaling_metric(mask_arr: np.ndarray) -> float:
        values = np.where(mask_arr, scaled_level, base_level)
        mult_series = pd.Series(dict(zip(entry_dates.to_numpy(), values)))
        sim = simulate_equity(trades, risk_pct=RISK_PCT, risk_multiplier=mult_series)
        return _dollar_profit_factor(sim)

    rng = np.random.default_rng(42)
    actual = _scaling_metric(is_scaled_mask)
    for name, shuffle_fn in [("rotation", rotation_shuffle), ("run_permutation", run_permutation_shuffle)]:
        nulls = np.array([_scaling_metric(shuffle_fn(is_scaled_mask, rng)) for _ in range(N_SHUFFLES)])
        finite = nulls[np.isfinite(nulls)]
        p_value = float(np.mean(nulls >= actual))
        print(
            f"{name:<16} actual={actual:.3f}  null_mean={finite.mean():.3f}  "
            f"null_p95={np.percentile(finite, 95):.3f}  p={p_value:.3f}"
        )


if __name__ == "__main__":
    main()
