"""Ornstein-Uhlenbeck parameter estimation via rolling OLS on log prices
(paper section 4.2): X_t = alpha + beta * X_{t-1} + eps_t, on log price series.

theta = -ln(beta) / dt   (dt = 1 trading day)
half_life = ln(2) / theta
p-value: two-sided test of beta != 1 (unit-root / no-reversion null), using the
OLS t-stat with a normal approximation (window sizes 60-252 make t~N indistinguishable
in practice, and the paper itself treats these p-values as descriptive, not exact tests).
"""

import math

import numpy as np
import pandas as pd

import config


def _norm_sf_two_sided(t_abs: pd.Series) -> pd.Series:
    """2 * P(Z > |t|) for standard normal Z, vectorized via math.erf."""
    def _one(t):
        if pd.isna(t):
            return np.nan
        return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t) / math.sqrt(2.0))))
    return t_abs.apply(_one)


def rolling_ou_params(log_price: pd.Series, window: int) -> pd.DataFrame:
    """Rolling OLS estimate of (theta, half_life, p_value) at every point in time
    using the trailing `window` observations, fully vectorized."""
    x = log_price.shift(1)
    y = log_price
    n = window

    sum_x = x.rolling(n).sum()
    sum_y = y.rolling(n).sum()
    sum_xy = (x * y).rolling(n).sum()
    sum_xx = (x * x).rolling(n).sum()
    sum_yy = (y * y).rolling(n).sum()

    sxx = sum_xx - (sum_x ** 2) / n  # centered sum of squares
    sxy = sum_xy - (sum_x * sum_y) / n

    beta = sxy / sxx
    alpha = (sum_y - beta * sum_x) / n

    sse = (
        sum_yy
        - 2 * alpha * sum_y
        - 2 * beta * sum_xy
        + n * alpha ** 2
        + 2 * alpha * beta * sum_x
        + beta ** 2 * sum_xx
    )
    sse = sse.clip(lower=0)
    s2 = sse / (n - 2)
    se_beta = np.sqrt(s2 / sxx)

    t_stat = (beta - 1.0) / se_beta
    p_value = _norm_sf_two_sided(t_stat.abs())

    theta = -np.log(beta.clip(lower=1e-6))  # dt = 1 trading day
    half_life = np.where(theta > 0, np.log(2) / theta, np.nan)

    return pd.DataFrame(
        {"beta": beta, "theta": theta, "half_life": half_life, "p_value": p_value},
        index=log_price.index,
    )


def estimate_ticker_ou_summary(price: pd.Series, sample_start: str, sample_end: str) -> dict:
    """Average theta/p_value/half_life over time (within a window length) and then
    across the three rolling window lengths, restricted to `sample_start:sample_end`
    (matches paper: 'parameter estimates are averaged across these windows for each asset')."""
    log_price = np.log(price)
    window_means = []
    for w in config.ROLLING_WINDOWS:
        est = rolling_ou_params(log_price, w)
        est_in_sample = est.loc[sample_start:sample_end]
        window_means.append(
            {
                "window": w,
                "theta": est_in_sample["theta"].mean(),
                "half_life": est_in_sample["half_life"].mean(),
                "p_value": est_in_sample["p_value"].mean(),
            }
        )
    wdf = pd.DataFrame(window_means)
    return {
        "theta": wdf["theta"].mean(),
        "half_life": wdf["half_life"].mean(),
        "p_value": wdf["p_value"].mean(),
        "per_window": wdf,
    }


def build_ou_summary_table(panel: pd.DataFrame, sample_start: str, sample_end: str) -> pd.DataFrame:
    rows = []
    for ticker in panel.columns:
        price = panel[ticker].dropna()
        if price.loc[sample_start:sample_end].shape[0] < max(config.ROLLING_WINDOWS) + 10:
            continue
        summary = estimate_ticker_ou_summary(price, sample_start, sample_end)
        rows.append({"ticker": ticker, "theta": summary["theta"],
                      "half_life": summary["half_life"], "p_value": summary["p_value"]})
    return pd.DataFrame(rows).set_index("ticker")
