"""Walk-forward A/B test: does Kalman-filter denoising (`strategy/kalman_filter.py`)
change the ADX-VWAP Refined config's performance?

Deliberately kept as a standalone research script, NOT wired into
`strategy/signals.py` or `app_pages/adx_vwap.py` -- the Kalman filter stays a
separate, independently-testable building block (see `app_pages/kalman_filter.py`
and `app_pages/adx_vwap_writeup.py`'s explicit "don't mix it into VWAP in
production code" convention). This script is the "test it yourself, don't
mix pages" the honest banners on both Strategie-Bestandteile pages point to.

Methodology: same yearly walk-forward as `research_adx_params.py` (9
independent calendar-year folds x 6 pairs, not a single static split), on top
of the Refined family (H1, ADX ceiling 25, theta x1.5, adx_n=10,
adx_window=20) -- the best-known candidate so far, so this asks "does Kalman
help the strongest baseline we have", not a strawman.

For each fold/pair, builds two signals off the *same* indicator dataframe:
one using deviation_t (raw VWAP deviation), one using deviation computed from
a Kalman-smoothed close (`strategy.kalman_filter.add_kalman_deviation`).
Everything else -- ADX conditions, prev-session trigger levels, ATR stop,
trade fills -- is identical, so any Sharpe difference is attributable to the
deviation signal alone, not a confound from changing multiple things at once.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.data import PAIRS
from strategy.indicators import (
    compute_adx,
    compute_prev_session_extremes,
    compute_regime_filter,
    compute_vwap_and_deviation,
)
from strategy.kalman_filter import add_kalman_deviation
from strategy.metrics import summarize
from strategy.real_data import load_all_pairs_real

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2026))  # full calendar years within the 2016-07-28..2026-07-28 dataset
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)
REFINED = dict(adx_n=10, adx_window=20, adx_ceiling=25.0, theta_multiplier=1.5)
THETA_WINDOW_BARS = 500

NOISE_FRACTIONS = [0.3, 0.5, 0.7]  # measurement_noise_fraction sweep for the Kalman variant


def build_indicators(raw_df: pd.DataFrame, adx_n: int, adx_window: int) -> pd.DataFrame:
    df = compute_vwap_and_deviation(raw_df, reset_hour=22)
    df = compute_prev_session_extremes(df)
    df = compute_adx(df, n=adx_n)
    df = compute_regime_filter(df, adx_window=adx_window)
    return df


def generate_signal_variant(
    df: pd.DataFrame, deviation_col: str, theta_window_bars: int, theta_multiplier: float, adx_ceiling: float
) -> pd.DataFrame:
    """Same logic as `strategy.signals.generate_signal`, parameterised by
    which deviation column drives the entry condition -- kept local to this
    script rather than adding a param back to the production signal module
    (see this script's docstring for why)."""
    df = df.copy()
    theta = df[deviation_col].rolling(window=theta_window_bars, min_periods=theta_window_bars // 2).std() * theta_multiplier
    df["theta"] = theta

    cond_adx_elevated = df["adx"] > df["adx_mean"]
    cond_adx_decaying = df["delta_adx"] <= 0
    cond_adx_ceiling = df["adx"] < adx_ceiling

    cond_at_high = df["close"] >= df["prev_high"]
    cond_above_vwap = df[deviation_col] > df["theta"]

    cond_at_low = df["close"] <= df["prev_low"]
    cond_below_vwap = df[deviation_col] < -df["theta"]

    short_mask = cond_at_high & cond_above_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling
    long_mask = cond_at_low & cond_below_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling

    df["signal"] = 0
    df.loc[short_mask.fillna(False), "signal"] = -1
    df.loc[long_mask.fillna(False), "signal"] = 1
    return df


def year_slice(signaled: pd.DataFrame, year: int) -> pd.DataFrame:
    return signaled[signaled.index.year == year]


def run_variant(data: dict, variant_name: str, deviation_col: str, noise_fraction: float | None = None) -> dict:
    cell_sharpes, cell_returns, cell_trades, cell_pos = [], [], [], []
    for pair in PAIRS:
        df = build_indicators(data[pair], REFINED["adx_n"], REFINED["adx_window"])
        if deviation_col == "deviation_kalman":
            df = add_kalman_deviation(df, measurement_noise_fraction=noise_fraction)
        signaled = generate_signal_variant(
            df, deviation_col, THETA_WINDOW_BARS, REFINED["theta_multiplier"], REFINED["adx_ceiling"]
        )
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

    if not cell_trades:
        return {"variant": variant_name, "n_cells": 0}
    return {
        "variant": variant_name,
        "n_cells": len(cell_trades),
        "total_trades": sum(cell_trades),
        "mean_sharpe": np.mean(cell_sharpes),
        "median_sharpe": np.median(cell_sharpes),
        "pct_cells_positive": np.mean(cell_pos),
        "mean_return_bps": np.mean(cell_returns) * 1e4,
    }


def main():
    print("Loading real Dukascopy H1 history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28", interval=dukascopy_python.INTERVAL_HOUR_1)

    print(f"\n=== Kalman-Filter A/B on Refined config, yearly walk-forward {YEARS[0]}-{YEARS[-1]}, all 6 pairs ===")
    rows = [run_variant(data, "raw (no Kalman)", "deviation")]
    for nf in NOISE_FRACTIONS:
        rows.append(run_variant(data, f"kalman (noise_fraction={nf})", "deviation_kalman", noise_fraction=nf))
        print(f"  noise_fraction={nf} done")

    screen = pd.DataFrame(rows).set_index("variant")
    print("\n", screen)


if __name__ == "__main__":
    main()
