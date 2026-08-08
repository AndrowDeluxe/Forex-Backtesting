"""Kalman filter as a reusable signal-processing building block.

Ported from a single paper's scalar random-walk state-space formulation
(Kili et al. 2025, "Kalman-Enhanced Deep Reinforcement Learning for
Noise-Resilient Algorithmic Trading in Volatile Gold Markets", Eq. 9-12):
each price is modelled as a noisy observation of a latent value,
y_t = x_t + v_t, x_{t+1} = x_t + w_t, with w_t ~ N(0, Q) and v_t ~ N(0, R).
Only that denoising layer is reused here -- the paper's DQN/PPO/RPPO agents
and its claimed performance (Sharpe 10-13, drawdown <1.5%, 244-822% return
uplift) are NOT reproduced or endorsed; those numbers are implausible for a
621-day out-of-sample window and were not independently re-derived. See the
paper_research record for this source for the full caveat.

Q/R are estimated from the series itself via a simple variance-ratio split
(`estimate_kalman_params`), not the paper's EM/MLE on the innovation
likelihood (Eq. 21) -- an honest approximation that picks a sensible
smoothing strength without a numerical optimizer, not a literal
reproduction of the paper's calibration.
"""

import numpy as np
import pandas as pd


def estimate_kalman_params(
    series: pd.Series, measurement_noise_fraction: float = 0.5
) -> tuple[float, float]:
    """Split the series' bar-to-bar variance between process noise Q (real
    drift) and measurement noise R (microstructure noise) by a fixed
    fraction, rather than the paper's EM optimization.

    `measurement_noise_fraction` close to 1 => most of the observed
    variance is treated as noise => aggressive smoothing. Close to 0 => the
    filter barely smooths at all. Uses the whole series' variance, so it
    sees "future" bars when estimating Q/R for a backtest -- a much smaller
    leak than using future *prices* directly, but not zero; for walk-forward
    use, estimate on a training window and pass `process_var`/
    `measurement_var` into `kalman_smooth` explicitly instead.
    """
    if not 0.0 <= measurement_noise_fraction <= 1.0:
        raise ValueError("measurement_noise_fraction must be in [0, 1]")

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
    """Causal scalar Kalman smoother (predict/update, Eq. 9-12).

    Each output value depends only on data up to and including that bar --
    no look-ahead in the recursion itself, same convention as every
    indicator in `strategy/indicators.py`. NaNs in the input are skipped
    (state simply isn't updated on that bar; the last estimate carries
    forward), so gaps don't corrupt the filter.

    If `process_var`/`measurement_var` are not given, both are estimated
    once from the whole input series via `estimate_kalman_params` -- see
    that function's docstring for the resulting (small) leak.
    """
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


def rolling_zscore(series: pd.Series, window: int = 252, min_periods: int | None = None) -> pd.Series:
    """Rolling z-score normalization (paper Eq. 13): (x - rolling_mean) /
    rolling_std over a trailing window. Causal by construction (`.rolling`
    only looks backward). Default window (252) matches the paper's
    ~1-trading-year lookback. Returns NaN where rolling std is 0 (flat
    input) rather than dividing by zero.
    """
    min_periods = min_periods if min_periods is not None else max(window // 4, 2)
    mean = series.rolling(window=window, min_periods=min_periods).mean()
    std = series.rolling(window=window, min_periods=min_periods).std()
    return (series - mean) / std.replace(0.0, np.nan)


def add_kalman_deviation(df: pd.DataFrame, measurement_noise_fraction: float = 0.5) -> pd.DataFrame:
    """Adds `close_kalman` (denoised close) and `deviation_kalman` (VWAP
    deviation recomputed against the denoised close) to a dataframe that
    already has `vwap` (from `strategy.indicators.compute_vwap_and_deviation`).

    Deliberately does NOT touch `close`, `open`, `high`, `low`, `vwap`,
    `prev_high`, `prev_low` -- those stay on real market prices so trade
    fills in `strategy/backtest.py` never execute against a synthetic
    filtered price. Only a *signal* built downstream (e.g. a VWAP-deviation
    threshold) is meant to read the denoised column; execution always reads
    the real one.
    """
    if "vwap" not in df.columns:
        raise ValueError("add_kalman_deviation requires 'vwap' -- run compute_vwap_and_deviation first")

    df = df.copy()
    df["close_kalman"] = kalman_smooth(df["close"], measurement_noise_fraction=measurement_noise_fraction)
    df["deviation_kalman"] = (df["close_kalman"] - df["vwap"]) / df["vwap"]
    return df
