"""Screen the three previously-untested, paper-native levers (Remark 1's
strict ADX-decay condition; the ADX lookback n and mean-window m from
Sec. 6.2's free-parameter list) on top of the one family that showed any
promise so far (H1, ADX ceiling 25, theta x1.5).

Methodology change from the earlier research_*.py scripts: instead of one
static in-sample/out-of-sample split (already used three times), this
evaluates every candidate across ALL available full calendar years
(2017-2025) as independent yearly folds. This uses the same underlying data
but reports a distribution across years/pairs rather than a single number,
which is what the earlier scripts' thin-trade-count problem actually called
for -- it does not "unlock" new out-of-sample data, it just measures
robustness properly.
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

YEARS = list(range(2017, 2026))  # full calendar years within the 2016-07-28..2026-07-28 dataset
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)
FIXED = dict(adx_ceiling=25.0, theta_multiplier=1.5)  # the one promising family found so far

GRID = {
    "strict_adx_decay": [False, True],
    "adx_n": [10, 14, 20],
    "adx_window": [10, 20, 30],
}


def year_slice(signaled: pd.DataFrame, year: int) -> pd.DataFrame:
    return signaled[(signaled.index.year == year)]


def main():
    print("Loading real Dukascopy H1 history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_HOUR_1)

    combos = [
        dict(strict_adx_decay=s, adx_n=n, adx_window=m)
        for s in GRID["strict_adx_decay"]
        for n in GRID["adx_n"]
        for m in GRID["adx_window"]
    ]

    print(f"\n=== Yearly walk-forward screen, {YEARS[0]}-{YEARS[-1]}, all 6 pairs ===")
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

        name = f"strict={combo['strict_adx_decay']} n={combo['adx_n']} m={combo['adx_window']}"
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
            }
        )
        print(f"  {name:35s} done ({sum(cell_trades)} trades across {len(cell_trades)} year-pair cells)")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)


if __name__ == "__main__":
    main()
