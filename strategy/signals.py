"""Composite signal S_t in {-1, 0, +1} (Eq. 14)."""

import pandas as pd

from strategy.indicators import compute_adaptive_theta


def generate_signal(
    df: pd.DataFrame,
    theta: float | pd.Series | None = None,
    theta_window_bars: int = 500,
    theta_multiplier: float = 1.0,
) -> pd.DataFrame:
    """Evaluate the four joint conditions of Eq. 14 and emit S_t.

    `theta`: fixed scalar, a precomputed Series, or None (default) to use the
    adaptive rolling-std threshold from `compute_adaptive_theta`.
    """
    df = df.copy()
    if theta is None:
        theta = compute_adaptive_theta(df, theta_window_bars, theta_multiplier)
    df["theta"] = theta

    cond_adx_elevated = df["adx"] > df["adx_mean"]
    cond_adx_decaying = df["delta_adx"] <= 0

    cond_at_high = df["close"] >= df["prev_high"]
    cond_above_vwap = df["deviation"] > df["theta"]

    cond_at_low = df["close"] <= df["prev_low"]
    cond_below_vwap = df["deviation"] < -df["theta"]

    short_mask = cond_at_high & cond_above_vwap & cond_adx_elevated & cond_adx_decaying
    long_mask = cond_at_low & cond_below_vwap & cond_adx_elevated & cond_adx_decaying

    df["signal"] = 0
    df.loc[short_mask.fillna(False), "signal"] = -1
    df.loc[long_mask.fillna(False), "signal"] = 1
    return df


def run_indicator_pipeline(
    df: pd.DataFrame,
    reset_hour: int = 22,
    adx_n: int = 14,
    adx_window: int = 20,
    theta_window_bars: int = 500,
    theta_multiplier: float = 1.0,
) -> pd.DataFrame:
    from strategy.indicators import (
        compute_adx,
        compute_prev_session_extremes,
        compute_regime_filter,
        compute_vwap_and_deviation,
    )

    out = compute_vwap_and_deviation(df, reset_hour=reset_hour)
    out = compute_prev_session_extremes(out)
    out = compute_adx(out, n=adx_n)
    out = compute_regime_filter(out, adx_window=adx_window)
    out = generate_signal(out, theta_window_bars=theta_window_bars, theta_multiplier=theta_multiplier)
    return out
