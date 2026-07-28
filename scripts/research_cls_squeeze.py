"""Test the CLS settlement-cutoff squeeze/VWAP-reversion hypothesis
(strategy/cls_squeeze.py) on real Dukascopy data: cutoff window 06:00-07:00
UTC, entry window 07:00-07:30 UTC (just after the cutoff, as London comes
online). EUR/USD at M5 (finer resolution for a 30-min entry window) and
M15, plus all 6 paper pairs at M15 as a broader check.

Same yearly-walk-forward methodology as the other research_*.py scripts
(2017-2025, 9 annual folds) - this is a new hypothesis/mechanism, not a
re-peek at an already-mined parameter family, but the methodology is kept
consistent regardless.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.cls_squeeze import run_cls_squeeze_pipeline
from strategy.data import PAIRS
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2026))
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=None)

CUTOFF = dict(cutoff_start_hour=6.0, cutoff_end_hour=7.0, entry_start_hour=7.0, entry_end_hour=9.0)


def yearly_walk_forward(signaled: pd.DataFrame, config: BacktestConfig) -> dict:
    cell_sharpes, cell_returns, cell_trades = [], [], []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        trades = simulate_trades(yr_df, config)
        s = summarize(trades, yr_df.index)
        if s["n_trades"] == 0:
            continue
        cell_sharpes.append(s["sharpe"])
        cell_returns.append(s["avg_return_pct"])
        cell_trades.append(s["n_trades"])
    if not cell_trades:
        return {"n_cells": 0, "total_trades": 0}
    return {
        "n_cells": len(cell_trades),
        "total_trades": sum(cell_trades),
        "mean_sharpe": np.mean(cell_sharpes),
        "median_sharpe": np.median(cell_sharpes),
        "pct_cells_positive": np.mean([r > 0 for r in cell_returns]),
        "mean_return_bps": np.mean(cell_returns) * 1e4,
    }


def main():
    # A max hold of ~10 bars at M15 (2.5h) / ~30 bars at M5 (2.5h) keeps a
    # trade from running all the way to the next midnight VWAP reset if
    # neither the stop nor the VWAP target ever fires.
    config_m5_reversion = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=30)
    config_m15_reversion = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=10)
    # Momentum: no VWAP target (price is already past VWAP at entry by
    # construction), ride it to the stop or the hold-time cap instead.
    config_m5_momentum = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=30, use_vwap_target=False)
    config_m15_momentum = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=10, use_vwap_target=False)

    print("=== EUR/USD, M5, reversion ===")
    eurusd_m5 = fetch_pair_history("EURUSD", "2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_MIN_5)
    signaled = run_cls_squeeze_pipeline(eurusd_m5, **CUTOFF)
    print(yearly_walk_forward(signaled, config_m5_reversion))

    print("\n=== EUR/USD, M15, reversion ===")
    eurusd_m15 = fetch_pair_history("EURUSD", "2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_MIN_15)
    signaled = run_cls_squeeze_pipeline(eurusd_m15, **CUTOFF)
    print(yearly_walk_forward(signaled, config_m15_reversion))

    print("\n=== All 6 pairs, M15, reversion ===")
    rows = []
    for pair in PAIRS:
        df = fetch_pair_history(pair, "2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_MIN_15)
        signaled = run_cls_squeeze_pipeline(df, **CUTOFF)
        result = yearly_walk_forward(signaled, config_m15_reversion)
        rows.append({"pair": pair, **result})
    print(pd.DataFrame(rows).set_index("pair"))

    print("\n=== EUR/USD, M5, MOMENTUM ===")
    signaled = run_cls_squeeze_pipeline(eurusd_m5, **CUTOFF, direction_mode="momentum")
    print(yearly_walk_forward(signaled, config_m5_momentum))

    print("\n=== EUR/USD, M15, MOMENTUM ===")
    signaled = run_cls_squeeze_pipeline(eurusd_m15, **CUTOFF, direction_mode="momentum")
    print(yearly_walk_forward(signaled, config_m15_momentum))

    print("\n=== All 6 pairs, M15, MOMENTUM ===")
    rows = []
    for pair in PAIRS:
        df = fetch_pair_history(pair, "2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_MIN_15)
        signaled = run_cls_squeeze_pipeline(df, **CUTOFF, direction_mode="momentum")
        result = yearly_walk_forward(signaled, config_m15_momentum)
        rows.append({"pair": pair, **result})
    print(pd.DataFrame(rows).set_index("pair"))


if __name__ == "__main__":
    main()
