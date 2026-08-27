"""Baustein 1: dynamic Hurst exponent via Detrended Fluctuation Analysis
(DFA-2, quadratic local detrending) - Peng et al. (1994) / Kantelhardt et
al. (2002) MF-DFA at moment order q=2, the exact estimator the FLPD paper
(ssrn-6880798, Sec 3.2/4.2) uses for its dynamic Hurst exponent H^T. Pure
numpy - no extra dependency (requirements.txt has no nolds/antropy).

The paper computes H^T on tick data (W=2000 ticks, stepped 200 ticks). This
repo only has bar data (Binance klines), so `window`/`step` here are in BARS
- a deliberate, disclosed translation, not a tick-level replication (see
resources/crypto-hurst-wyckoff-cycles.md)."""

import numpy as np
import pandas as pd

DEFAULT_WINDOW_SIZES = (10, 16, 25, 40, 63, 100)

_HAT_CACHE: dict[tuple[int, int], np.ndarray] = {}


def _hat_matrix(s: int, order: int) -> np.ndarray:
    """OLS projection (hat) matrix for detrending length-s segments with an
    order-`order` polynomial: fitted = H @ segment. Depends only on (s,
    order), so it is computed once and cached - this is what makes rolling
    DFA over tens of thousands of bars fast enough for a research script
    (no per-segment np.polyfit call, a single small matmul instead)."""
    key = (s, order)
    if key not in _HAT_CACHE:
        t = np.arange(s, dtype=float)
        X = np.vander(t, order + 1, increasing=True)  # (s, order+1): [1, t, t^2, ...]
        _HAT_CACHE[key] = X @ np.linalg.pinv(X)  # (s, s)
    return _HAT_CACHE[key]


def _fluctuation(profile: np.ndarray, s: int, order: int = 2) -> float:
    """RMS fluctuation F(s): splits `profile` into non-overlapping length-s
    segments from BOTH ends (standard DFA convention - halves edge-data
    waste vs. segmenting from the start only), detrends each with an
    order-`order` polynomial via the precomputed hat matrix, returns
    sqrt(mean squared residual) pooled across all segments/both directions."""
    n = len(profile)
    n_seg = n // s
    if n_seg < 2:
        return np.nan
    hat = _hat_matrix(s, order)
    sq_devs = []
    for direction in (profile, profile[::-1]):
        segments = direction[: n_seg * s].reshape(n_seg, s)
        fitted = segments @ hat.T
        sq_devs.append(np.mean((segments - fitted) ** 2, axis=1))
    return float(np.sqrt(np.mean(np.concatenate(sq_devs))))


def dfa_hurst(log_returns: np.ndarray, window_sizes=DEFAULT_WINDOW_SIZES, order: int = 2) -> float:
    """Single-window DFA Hurst estimate: slope of log F(s) vs log s (linear
    regression across `window_sizes`). NaN if fewer than 3 (s, F(s)) points
    survive - e.g. `log_returns` shorter than ~2x the largest window size."""
    x = np.asarray(log_returns, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < max(window_sizes) * 2:
        return np.nan
    profile = np.cumsum(x - x.mean())
    log_fs, log_ss = [], []
    for s in window_sizes:
        f = _fluctuation(profile, s, order=order)
        if np.isfinite(f) and f > 0:
            log_fs.append(np.log(f))
            log_ss.append(np.log(s))
    if len(log_fs) < 3:
        return np.nan
    slope, _ = np.polyfit(log_ss, log_fs, 1)
    return float(slope)


def rolling_hurst(close: pd.Series, window: int = 500, step: int = 24, window_sizes=DEFAULT_WINDOW_SIZES) -> pd.Series:
    """Dynamic Hurst exponent H^T (paper Sec 3.2): DFA on the trailing
    `window` log-returns, recomputed every `step` bars and forward-filled
    in between (H^T is a state estimate, not a per-bar quantity - matches
    the paper's own "stepped" windows). Strictly causal: the value assigned
    at bar t only ever uses log-returns up to and including bar t, so it is
    also valid to use directly as a same-bar signal (no extra shift needed
    before consuming it, unlike a raw indicator that peeks at the current
    bar's close - H^T by construction never does)."""
    log_ret = np.log(close).diff()
    n = len(close)
    values = np.full(n, np.nan)
    for i in range(window, n, step):
        values[i] = dfa_hurst(log_ret.iloc[i - window + 1 : i + 1].to_numpy(), window_sizes=window_sizes)
    return pd.Series(values, index=close.index).ffill()


def hurst_collapse_signal(ht: pd.Series, z_window: int = 50, z_thresh: float = 2.0) -> pd.Series:
    """Boolean collapse flag (paper Sec 3.2's own criterion: H^T falls more
    than 2 rolling standard deviations): rolling z-score of delta-H over the
    trailing `z_window` changes, |z| > z_thresh. Simpler than the paper's
    full Chu-Stinchcombe-White CUSUM test - deliberately, since a heavier
    change-point estimator hasn't earned its complexity anywhere else in
    this repo's regime-filter attempts (see resources/trend-following-
    momentum.md's GMM-regime-filter finding). Causal (trailing rolling
    window, no centering)."""
    dh = ht.diff()
    mu = dh.rolling(z_window, min_periods=max(z_window // 2, 5)).mean()
    sd = dh.rolling(z_window, min_periods=max(z_window // 2, 5)).std()
    z = (dh - mu) / sd.replace(0, np.nan)
    return (z.abs() > z_thresh).fillna(False)
