"""Causal scalar Kalman smoother, self-contained copy for ou_paper_backtest's own
use (adapted from strategy/kalman_filter.py's kalman_smooth/estimate_kalman_params --
not imported directly since that module isn't committed to the repo yet and
ou_paper_backtest ships independently). Same state-space model: each price is a
noisy observation of a latent value, y_t = x_t + v_t, x_{t+1} = x_t + w_t."""

import numpy as np
import pandas as pd


def estimate_kalman_params(series: pd.Series, measurement_noise_fraction: float = 0.5) -> tuple[float, float]:
    diffs = series.dropna().diff().dropna()
    if diffs.empty:
        return 1e-8, 1e-8
    total_var = max(float(diffs.var()), 1e-12)
    r = total_var * measurement_noise_fraction
    q = total_var * (1 - measurement_noise_fraction)
    return max(q, 1e-12), max(r, 1e-12)


def kalman_smooth(
    series: pd.Series,
    process_var: float | None = None,
    measurement_var: float | None = None,
    measurement_noise_fraction: float = 0.5,
) -> pd.Series:
    """Causal predict/update recursion -- each output depends only on data up to and
    including that bar, no look-ahead in the recursion itself. Q/R default to a
    whole-series variance split (small look-ahead leak, same caveat as the original)."""
    values = series.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n == 0:
        return pd.Series(out, index=series.index)

    if process_var is None or measurement_var is None:
        q, r = estimate_kalman_params(series, measurement_noise_fraction)
        process_var = q if process_var is None else process_var
        measurement_var = r if measurement_var is None else measurement_var

    first_valid = series.first_valid_index()
    if first_valid is None:
        return pd.Series(out, index=series.index)

    start = series.index.get_loc(first_valid)
    x_est = values[start]
    p_est = measurement_var
    out[start] = x_est

    for t in range(start + 1, n):
        y = values[t]
        if np.isnan(y):
            out[t] = x_est
            continue
        x_pred = x_est
        p_pred = p_est + process_var
        gain = p_pred / (p_pred + measurement_var)
        x_est = x_pred + gain * (y - x_pred)
        p_est = (1 - gain) * p_pred
        out[t] = x_est

    return pd.Series(out, index=series.index)
