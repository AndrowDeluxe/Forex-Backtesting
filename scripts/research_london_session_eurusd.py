"""ADX-VWAP strategy, EUR/USD only, restricted to the London session window
(08:00-16:00 UTC), swept across bar frequencies M5/M15/M30/H1 - both the
paper's literal Eq. 14 and our previously-found refined configuration
(adx_ceiling=25, theta x1.5, adx_n=10, adx_window=20).

Methodology: yearly walk-forward folds (2017-2025, 9 independent annual
reads), same approach as scripts/research_adx_params.py - this specific
combination (this session window, this pair only, this timeframe set)
hasn't been screened before, but using yearly folds rather than one static
split is simply more robust, not a matter of "fresh vs. stale" data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history
from strategy.signals import run_indicator_pipeline

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
YEARS = list(range(2017, 2026))
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)

TIMEFRAMES = {
    "M5": dukascopy_python.INTERVAL_MIN_5,
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "M30": dukascopy_python.INTERVAL_MIN_30,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
}

SIGNAL_CONFIGS = {
    "Pure Eq. 14": dict(),
    "Refined (adx_ceiling=25, theta x1.5, n=10, m=20)": dict(
        adx_ceiling=25.0, theta_multiplier=1.5, adx_n=10, adx_window=20
    ),
}

LONDON_WINDOW = dict(session_start_hour=8, session_end_hour=16)


def main():
    print("Loading EUR/USD history at M5/M15/M30/H1 (cached after first run)...")
    data = {tf: fetch_pair_history("EURUSD", START, END, interval=interval) for tf, interval in TIMEFRAMES.items()}
    for tf, df in data.items():
        print(f"  {tf}: {df.shape}")

    rows = []
    for tf in TIMEFRAMES:
        for config_name, config_params in SIGNAL_CONFIGS.items():
            signaled = run_indicator_pipeline(data[tf], **LONDON_WINDOW, **config_params)
            cell_sharpes, cell_returns, cell_trades = [], [], []
            for year in YEARS:
                yr_df = signaled[signaled.index.year == year]
                if yr_df.empty:
                    continue
                trades = simulate_trades(yr_df, BASE_CONFIG)
                s = summarize(trades, yr_df.index)
                if s["n_trades"] == 0:
                    continue
                cell_sharpes.append(s["sharpe"])
                cell_returns.append(s["avg_return_pct"])
                cell_trades.append(s["n_trades"])

            if cell_trades:
                rows.append(
                    {
                        "timeframe": tf,
                        "config": config_name,
                        "n_cells": len(cell_trades),
                        "total_trades": sum(cell_trades),
                        "mean_sharpe": np.mean(cell_sharpes),
                        "median_sharpe": np.median(cell_sharpes),
                        "pct_cells_positive": np.mean([r > 0 for r in cell_returns]),
                        "mean_return_bps": np.mean(cell_returns) * 1e4,
                    }
                )
            else:
                rows.append({"timeframe": tf, "config": config_name, "n_cells": 0, "total_trades": 0})
            print(f"  {tf} | {config_name} done")

    result = pd.DataFrame(rows).set_index(["timeframe", "config"]).sort_values("mean_sharpe", ascending=False)
    print("\n=== EUR/USD, London session 08-16 UTC, yearly walk-forward 2017-2025 ===")
    print(result)


if __name__ == "__main__":
    main()
