"""Circular block-bootstrap Monte Carlo on the final locked strategy's daily
returns: resample blocks (not single days) with replacement to preserve
short-term autocorrelation/regime persistence, rebuild many alternate equity
paths from the SAME historical return distribution actually experienced, and
report the resulting spread of Sharpe/Calmar/max-drawdown/final-equity.

Important interpretation note (see the "Fertige Strategien" page): this
quantifies SEQUENCE risk -- how much the realized path/drawdown depended on
WHEN the good and bad stretches happened to occur -- not "would this work in
some other unseen market regime." It reshuffles the same history, it doesn't
invent a new one. Complementary to, not a substitute for, the DAX
cross-market check or a genuine walk-forward test.
"""

import numpy as np
import pandas as pd

import config


def block_bootstrap_paths(
    daily_returns: pd.Series, block_size: int = 20, n_sims: int = 2000, seed: int = 42
) -> np.ndarray:
    """Circular block bootstrap: returns an (n_sims, n_days) array of resampled
    daily-return paths. Circular wraparound (block start can be within block_size
    of the series' end) keeps every path exactly n_days long without a shrinking
    last block."""
    values = daily_returns.to_numpy()
    n = len(values)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))

    starts = rng.integers(0, n, size=(n_sims, n_blocks))
    paths = np.empty((n_sims, n_blocks * block_size))
    offsets = np.arange(block_size)
    for b in range(n_blocks):
        idx = (starts[:, b][:, None] + offsets[None, :]) % n
        paths[:, b * block_size:(b + 1) * block_size] = values[idx]
    return paths[:, :n]


def summarize_paths(paths: np.ndarray, initial_equity: float = config.INITIAL_EQUITY) -> dict:
    equity = initial_equity * np.cumprod(1.0 + paths, axis=1)
    n_days = paths.shape[1]
    years = n_days / config.TRADING_DAYS_PER_YEAR

    final_equity = equity[:, -1]
    total_return = final_equity / initial_equity - 1.0
    ann_return = np.sign(1 + total_return) * np.abs(1 + total_return) ** (1 / years) - 1.0

    running_max = np.maximum.accumulate(equity, axis=1)
    drawdown = equity / running_max - 1.0
    max_dd = drawdown.min(axis=1)

    ann_vol = paths.std(axis=1) * np.sqrt(config.TRADING_DAYS_PER_YEAR)
    sharpe = np.divide(ann_return, ann_vol, out=np.full_like(ann_return, np.nan), where=ann_vol > 0)
    calmar = np.divide(ann_return, np.abs(max_dd), out=np.full_like(ann_return, np.nan), where=max_dd < 0)

    return {
        "equity_paths": equity,
        "final_equity": final_equity,
        "total_return_pct": total_return * 100,
        "max_drawdown_pct": max_dd * 100,
        "sharpe": sharpe,
        "calmar": calmar,
    }


def percentile_bands(equity_paths: np.ndarray, index: pd.DatetimeIndex, percentiles=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    bands = np.percentile(equity_paths, percentiles, axis=0)
    return pd.DataFrame(bands.T, index=index, columns=[f"p{p}" for p in percentiles])


def run_monte_carlo(
    daily_returns: pd.Series, initial_equity: float = config.INITIAL_EQUITY,
    block_size: int = 20, n_sims: int = 2000, seed: int = 42,
) -> dict:
    paths = block_bootstrap_paths(daily_returns, block_size=block_size, n_sims=n_sims, seed=seed)
    summary = summarize_paths(paths, initial_equity=initial_equity)
    bands = percentile_bands(summary["equity_paths"], daily_returns.index)
    return {"summary": summary, "bands": bands}
