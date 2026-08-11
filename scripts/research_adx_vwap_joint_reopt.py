"""Joint re-optimization of theta_multiplier x adx_ceiling, now holding the
LATER-discovered adx_n=10/adx_window=20 fixed throughout.

Why this is needed: `REFINED_PARAMS` in app_pages/adx_vwap.py
(adx_n=10, adx_window=20, adx_ceiling=25.0, theta_multiplier=1.5) glues
together two parameters found in two SEPARATE, SEQUENTIAL research rounds --
adx_ceiling=25.0/theta_multiplier=1.5 were found first (before adx_n/
adx_window were even swept), then adx_n=10/adx_window=20 were found later
via research_adx_params.py's yearly walk-forward, with adx_ceiling/
theta_multiplier simply held fixed at their earlier values throughout that
later sweep. The two halves of REFINED_PARAMS have never been validated
TOGETHER. This script closes that gap: same yearly-walk-forward methodology
as research_adx_params.py (more robust than a single static IS/OOS split,
per that script's own reasoning), same H1 data, same 6 pairs, same
2017-2025 fold years -- just a different two-parameter grid.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.data import PAIRS
from strategy.metrics import summarize
from strategy.real_data import load_all_pairs_real
from strategy.signals import run_indicator_pipeline

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2026))
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)
FIXED = dict(adx_n=10, adx_window=20)  # the walk-forward winner from research_adx_params.py

GRID = {
    "theta_multiplier": [1.0, 1.25, 1.5, 1.75, 2.0],
    "adx_ceiling": [20.0, 25.0, 30.0, 35.0, None],
}

CURRENT_REFINED = dict(theta_multiplier=1.5, adx_ceiling=25.0)  # today's app_pages/adx_vwap.py REFINED_PARAMS


def year_slice(signaled: pd.DataFrame, year: int) -> pd.DataFrame:
    return signaled[(signaled.index.year == year)]


def main():
    print("Loading real Dukascopy H1 history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_HOUR_1)

    combos = [
        dict(theta_multiplier=tm, adx_ceiling=ac)
        for tm in GRID["theta_multiplier"]
        for ac in GRID["adx_ceiling"]
    ]

    print(f"\n=== Joint theta_multiplier x adx_ceiling walk-forward, {YEARS[0]}-{YEARS[-1]}, all 6 pairs, adx_n=10/adx_window=20 fixed ===")
    rows = []
    for combo in combos:
        cell_sharpes, cell_returns, cell_trades, cell_pos = [], [], [], []
        for pair in PAIRS:
            signaled = run_indicator_pipeline(data[pair], **FIXED, **combo)
            for year in YEARS:
                yr_df = year_slice(signaled, year)
                if yr_df.empty:
                    continue
                trades = simulate_trades(yr_df, BASE_CONFIG)
                s = summarize(trades, yr_df.index)
                if s["n_trades"] == 0:
                    continue
                cell_sharpes.append(s["sharpe"])
                cell_returns.append(s["avg_return_pct"])
                cell_trades.append(s["n_trades"])
                cell_pos.append(s["avg_return_pct"] > 0)

        name = f"theta_mult={combo['theta_multiplier']} adx_ceiling={combo['adx_ceiling']}"
        if not cell_trades:
            rows.append({"candidate": name, "n_cells": 0})
            continue
        rows.append(
            {
                "candidate": name,
                "n_cells": len(cell_trades),
                "total_trades": sum(cell_trades),
                "mean_sharpe": np.mean(cell_sharpes),
                "median_sharpe": np.median(cell_sharpes),
                "pct_cells_positive": np.mean(cell_pos),
                "mean_return_bps": np.mean(cell_returns) * 1e4,
                "is_current_refined": combo == CURRENT_REFINED,
            }
        )
        marker = "  <-- CURRENT REFINED_PARAMS" if combo == CURRENT_REFINED else ""
        print(f"  {name:40s} done ({sum(cell_trades)} trades across {len(cell_trades)} year-pair cells){marker}")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)

    print("\n=== Current REFINED_PARAMS vs. the best-found combo ===")
    current_row = screen[screen["is_current_refined"] == True]  # noqa: E712
    best_row = screen.iloc[[0]]
    print("Current (theta_mult=1.5, adx_ceiling=25.0):\n", current_row)
    print("\nBest found:\n", best_row)

    return screen


if __name__ == "__main__":
    main()
