"""Performance + significance metrics for the one-trade-per-day intraday-
momentum construction. Self-contained rather than reusing
`strategy/metrics.py` -- that module's `summarize`/`trades_to_daily_returns`
assume ADX-VWAP-specific columns (adx_at_entry, atr_at_entry) that don't
apply here, and this signal already produces exactly one row per trading
day, so no daily-aggregation step is needed at all.

No new dependency: the permutation test and OLS beta are hand-rolled with
numpy (this repo's requirements.txt has no statsmodels/scipy).
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def annualized_sharpe(daily_returns: pd.Series) -> float:
    if daily_returns.empty or daily_returns.std(ddof=1) == 0:
        return 0.0
    return float(daily_returns.mean() / daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def sortino_ratio(daily_returns: pd.Series, mar: float = 0.0) -> float:
    """Annualized Sortino ratio (MAR=0, downside deviation = RMS of
    below-MAR returns) -- Seeck (2026)'s primary performance metric."""
    if daily_returns.empty:
        return 0.0
    downside = daily_returns[daily_returns < mar] - mar
    if downside.empty:
        return np.inf if daily_returns.mean() > mar else 0.0
    downside_dev = np.sqrt((downside**2).mean())
    if downside_dev == 0:
        return 0.0
    return float((daily_returns.mean() - mar) / downside_dev * np.sqrt(TRADING_DAYS_PER_YEAR))


def max_drawdown(daily_returns: pd.Series) -> float:
    if daily_returns.empty:
        return 0.0
    curve = (1 + daily_returns).cumprod()
    running_max = curve.cummax()
    return float((curve / running_max - 1.0).min())


def ols_beta_and_permutation_pvalue(
    returns: np.ndarray, signal: np.ndarray, n_perm: int = 5000, seed: int = 42
) -> tuple[float, float]:
    """beta of r_day = alpha + beta*sign(r1) + eps via the closed-form
    single-regressor OLS slope, plus a two-sided permutation p-value
    (shuffle the signal labels `n_perm` times, compare |beta| to the
    permutation distribution) -- same spirit as Seeck (2026) Sec. 3.3's
    permutation test, hand-rolled since no statsmodels dependency exists
    in this repo.
    """
    x = np.asarray(signal, dtype=float)
    y = np.asarray(returns, dtype=float)
    if len(x) < 10 or x.std() == 0:
        return 0.0, 1.0

    x_c = x - x.mean()
    beta = float(np.dot(x_c, y - y.mean()) / np.dot(x_c, x_c))

    rng = np.random.default_rng(seed)
    perm_betas = np.empty(n_perm)
    y_c = y - y.mean()
    for i in range(n_perm):
        xp = rng.permutation(x)
        xp_c = xp - xp.mean()
        denom = np.dot(xp_c, xp_c)
        perm_betas[i] = np.dot(xp_c, y_c) / denom if denom != 0 else 0.0

    p_value = float(np.mean(np.abs(perm_betas) >= abs(beta)))
    return beta, p_value


def summarize_period(trades: pd.DataFrame, return_col: str = "net_return") -> dict:
    """One row of headline stats for a (pair, period, cost-state) cell."""
    if trades.empty:
        return {
            "n_trades": 0, "beta": np.nan, "p_value": np.nan, "sharpe": np.nan,
            "sortino": np.nan, "win_rate": np.nan, "max_drawdown": np.nan,
            "avg_return_bps": np.nan,
        }
    beta, p_value = ols_beta_and_permutation_pvalue(
        trades["raw_return"].to_numpy(), trades["direction"].to_numpy()
    )
    r = trades[return_col]
    return {
        "n_trades": len(trades),
        "beta": beta,
        "p_value": p_value,
        "sharpe": annualized_sharpe(r),
        "sortino": sortino_ratio(r),
        "win_rate": float((r > 0).mean()),
        "max_drawdown": max_drawdown(r),
        "avg_return_bps": float(r.mean() * 1e4),
    }
