"""Systematic stop_atr_mult sweep -- the fourth free lever from Paper 5's
Sec. 5.3 ("a short entered at H_{t-1} should be stopped out on a confirmed
close beyond it by a margin proportional to ATR"), which every prior round
of ADX-VWAP research held fixed at 0.5 without ever sweeping it. Built on
top of the signal config found by research_adx_vwap_joint_reopt.py: rather
than the top-of-list (theta_mult=2.0, adx_ceiling=25.0, only 52 trades
across 22/54 year-pair cells -- a thin-sample result matching the pattern
this repo has repeatedly flagged as unreliable elsewhere), this uses the
broader-coverage runner-up (theta_mult=1.5, adx_ceiling=35.0: higher mean
Sharpe than today's REFINED_PARAMS, 352 trades across 53/54 cells).
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
SIGNAL_PARAMS = dict(adx_n=10, adx_window=20, theta_multiplier=1.5, adx_ceiling=35.0)
STOP_ATR_GRID = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def year_slice(signaled: pd.DataFrame, year: int) -> pd.DataFrame:
    return signaled[(signaled.index.year == year)]


def main():
    print("Loading real Dukascopy H1 history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_HOUR_1)

    print("Pre-computing signal columns once per pair (signal params are fixed across this sweep)...")
    signaled_by_pair = {pair: run_indicator_pipeline(data[pair], **SIGNAL_PARAMS) for pair in PAIRS}

    print(f"\n=== stop_atr_mult walk-forward, {YEARS[0]}-{YEARS[-1]}, all 6 pairs, signal fixed at {SIGNAL_PARAMS} ===")
    rows = []
    for stop_mult in STOP_ATR_GRID:
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_mult)
        cell_sharpes, cell_returns, cell_trades, cell_pos = [], [], [], []
        stop_exit_frac = []
        for pair in PAIRS:
            signaled = signaled_by_pair[pair]
            for year in YEARS:
                yr_df = year_slice(signaled, year)
                if yr_df.empty:
                    continue
                trades = simulate_trades(yr_df, cfg)
                if trades.empty:
                    continue
                s = summarize(trades, yr_df.index)
                cell_sharpes.append(s["sharpe"])
                cell_returns.append(s["avg_return_pct"])
                cell_trades.append(s["n_trades"])
                cell_pos.append(s["avg_return_pct"] > 0)
                stop_exit_frac.append((trades["exit_reason"] == "stop").mean())

        name = f"stop_atr_mult={stop_mult}"
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
                "mean_stop_exit_frac": np.mean(stop_exit_frac),
            }
        )
        print(f"  {name:20s} done ({sum(cell_trades)} trades across {len(cell_trades)} year-pair cells)")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)
    return screen


if __name__ == "__main__":
    main()
