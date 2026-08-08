"""Research script: Gap-Fade EUR/USD & GBP/USD.

Two parts:
1. In-sample sanity check (2000-2015): reproduce Caporale & Plastun (2016)'s
   own threshold sweep on this repo's Dukascopy data. Trade COUNTS should
   land in the same ballpark as their Table 7 (not an exact match -- their
   data vendor differs -- but close enough to trust the gap-detection logic
   before believing anything OOS).
2. Honest out-of-sample test (2016 - today): fixed at the paper's own,
   NOT re-optimised thresholds (EUR/USD 0.10%, GBP/USD 0.05%), with a
   cost-sensitivity sweep the paper itself never disclosed, and a
   year-by-year breakdown.

Run: python scripts/research_gap_fade.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gap_fade.data import fetch_daily
from gap_fade.engine import (
    DEFAULT_THRESHOLD_PCT,
    compute_gap_trades,
    summarize,
    threshold_sweep,
    yearly_breakdown,
)

IS_START, IS_END = "2000-01-01", "2015-12-31"
OOS_START, OOS_END = "2016-01-01", "2026-08-09"
SPREAD_SWEEP_BPS = [0.0, 0.5, 1.0, 1.5, 2.0]

# Paper's Table 7 trade counts (2000-2015), for the sanity-check printout only.
PAPER_COUNTS = {
    "EURUSD": {0.05: 92, 0.10: 58, 0.15: 40, 0.20: 29, 0.25: 23},
    "GBPUSD": {0.05: 221, 0.10: 113, 0.15: 69, 0.20: 41, 0.25: 27},
}


def _header(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def run_pair(pair: str) -> dict:
    threshold = DEFAULT_THRESHOLD_PCT[pair]
    full = fetch_daily(pair, IS_START, OOS_END)
    is_df = full.loc[IS_START:IS_END]
    oos_df = full.loc[OOS_START:OOS_END]

    _header(f"{pair} -- 1) In-Sample Sanity Check (2000-2015, gross, threshold sweep)")
    sweep = threshold_sweep(is_df, spread_bps=0.0)
    sweep["paper_trades"] = [PAPER_COUNTS[pair][t] for t in sweep["threshold_pct"]]
    print(sweep[["threshold_pct", "n_trades", "paper_trades", "win_rate_pct", "total_pnl_pct"]].to_string(index=False))
    print(
        "(n_trades vs. paper_trades: same ballpark expected, not exact -- "
        "different data vendor. Large divergence would mean the gap logic "
        "or day-boundary convention is wrong, not just noise.)"
    )

    _header(f"{pair} -- 2) Out-of-Sample (2016 - today), fixed threshold {threshold}%, cost sensitivity")
    for bps in SPREAD_SWEEP_BPS:
        trades = compute_gap_trades(oos_df, threshold, spread_bps=bps)
        s = summarize(trades)
        print(f"  spread_bps={bps:>4.1f}  ->  {s}")

    spread_used = 1.0
    _header(f"{pair} -- 3) Out-of-Sample year-by-year (spread_bps={spread_used})")
    trades_oos = compute_gap_trades(oos_df, threshold, spread_bps=spread_used)
    yearly = yearly_breakdown(trades_oos)
    print(yearly.to_string())
    if not yearly.empty:
        pos_years = int((yearly["total_pnl_pct"] > 0).sum())
        print(f"\n{pos_years}/{len(yearly)} years net positive.")

    return {
        "pair": pair,
        "threshold_pct": threshold,
        "is_sweep": sweep,
        "oos_summary_by_cost": {
            bps: summarize(compute_gap_trades(oos_df, threshold, spread_bps=bps)) for bps in SPREAD_SWEEP_BPS
        },
        "oos_yearly": yearly,
    }


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    results = {pair: run_pair(pair) for pair in DEFAULT_THRESHOLD_PCT}
