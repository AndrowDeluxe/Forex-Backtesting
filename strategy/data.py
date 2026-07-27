"""Synthetic intraday FX OHLCV generator.

Produces data with three properties the strategy needs to be exercisable at all:
regime-switching trend/vol (so ADX has genuine trending vs. ranging periods),
a slow mean-reverting pull toward a fundamental (so VWAP reversion is a real,
not accidental, property of the series), and session-shaped volume.

This is NOT a claim about real FX dynamics. It lets the pipeline and backtest
engine be validated end-to-end without a data license. Results on this data
show whether the strategy logic behaves as designed, not whether it has a
real-world edge.
"""

import numpy as np
import pandas as pd

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]

_BASE_PRICE = {
    "EURUSD": 1.0900,
    "GBPUSD": 1.2700,
    "USDJPY": 148.00,
    "USDCHF": 0.8800,
    "AUDUSD": 0.6600,
    "USDCAD": 1.3600,
}

# Annualised vol by regime (range-bound vs. trending), roughly realistic for majors.
_REGIME_VOL = {"range": 0.06, "trend": 0.11}
_REGIME_DRIFT = {"range": 0.0, "trend": 0.18}  # annualised drift while trending, sign randomised per episode


def _build_utc_index(start: str, end: str, freq_minutes: int) -> pd.DatetimeIndex:
    idx = pd.date_range(start, end, freq=f"{freq_minutes}min", tz="UTC")
    # FX week: closed roughly Fri 22:00 UTC -> Sun 22:00 UTC
    dow = idx.dayofweek
    hour = idx.hour
    closed = (dow == 5) | ((dow == 6) & (hour < 22)) | ((dow == 4) & (hour >= 22))
    return idx[~closed]


def _simulate_regime_path(n: int, rng: np.random.Generator, mean_episode_bars: int) -> np.ndarray:
    """Two-state regime path (0=range, 1=trend) with geometric sojourn times."""
    regimes = np.empty(n, dtype=np.int8)
    i = 0
    state = rng.integers(0, 2)
    while i < n:
        dur = max(1, rng.geometric(1.0 / mean_episode_bars))
        dur = min(dur, n - i)
        regimes[i : i + dur] = state
        i += dur
        state = 1 - state
    return regimes


def generate_synthetic_ohlcv(
    pair: str,
    start: str = "2023-01-01",
    end: str = "2026-01-01",
    freq_minutes: int = 15,
    mean_reversion_kappa: float = 0.015,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate one synthetic OHLCV series for `pair` at `freq_minutes` resolution.

    Columns: open, high, low, close, volume. UTC DatetimeIndex.
    """
    if pair not in _BASE_PRICE:
        raise ValueError(f"unknown pair {pair}, expected one of {PAIRS}")

    rng = np.random.default_rng(seed if seed is not None else abs(hash(pair)) % (2**32))
    idx = _build_utc_index(start, end, freq_minutes)
    n = len(idx)

    bars_per_year = 252 * (24 * 60 / freq_minutes) * (5 / 7)
    dt = 1.0 / bars_per_year

    mean_episode_bars = int((3 * 24 * 60) / freq_minutes)  # ~3-day average regime length
    regimes = _simulate_regime_path(n, rng, mean_episode_bars)

    # Randomise trend direction per trending episode.
    episode_id = np.cumsum(np.r_[1, np.diff(regimes) != 0])
    trend_sign = pd.Series(rng.choice([-1.0, 1.0], size=episode_id.max() + 1)[episode_id])

    sigma = np.where(regimes == 1, _REGIME_VOL["trend"], _REGIME_VOL["range"]) * np.sqrt(dt)
    drift = np.where(regimes == 1, _REGIME_DRIFT["trend"] * trend_sign.values, 0.0) * dt

    log_price = np.empty(n)
    log_price[0] = np.log(_BASE_PRICE[pair])
    fundamental = np.empty(n)
    fundamental[0] = log_price[0]
    fund_halflife_bars = int((10 * 24 * 60) / freq_minutes)
    fund_alpha = 1 - 0.5 ** (1 / fund_halflife_bars)

    z = rng.standard_normal(n)
    for t in range(1, n):
        fundamental[t] = fundamental[t - 1] + fund_alpha * (log_price[t - 1] - fundamental[t - 1]) * 0.0 \
            + drift[t] * 0.15  # fundamental drifts slowly with a fraction of the realised trend
        reversion = -mean_reversion_kappa * (log_price[t - 1] - fundamental[t - 1]) * dt * bars_per_year
        log_price[t] = log_price[t - 1] + drift[t] + reversion + sigma[t] * z[t]

    close = np.exp(log_price)
    open_ = np.r_[close[0], close[:-1]]

    intrabar_vol = sigma * np.abs(rng.standard_normal(n)) * 1.4
    high = np.maximum(open_, close) + intrabar_vol * close
    low = np.minimum(open_, close) - intrabar_vol * close

    hour = idx.hour + idx.minute / 60.0
    # Session activity: London (7-16 UTC) and NY (12-21 UTC) with an overlap bump.
    session_curve = (
        0.35
        + 0.9 * np.exp(-0.5 * ((hour - 9.0) / 3.0) ** 2)
        + 1.1 * np.exp(-0.5 * ((hour - 14.5) / 2.5) ** 2)
    )
    vol_noise = rng.lognormal(mean=0.0, sigma=0.35, size=n)
    volume = np.round(session_curve * vol_noise * 1000).astype(int)
    volume = np.maximum(volume, 1)

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )
    df.index.name = "timestamp"
    return df


def generate_all_pairs(
    start: str = "2023-01-01",
    end: str = "2026-01-01",
    freq_minutes: int = 15,
    seed: int | None = 42,
) -> dict[str, pd.DataFrame]:
    out = {}
    for i, pair in enumerate(PAIRS):
        pair_seed = None if seed is None else seed + i
        out[pair] = generate_synthetic_ohlcv(pair, start, end, freq_minutes, seed=pair_seed)
    return out
