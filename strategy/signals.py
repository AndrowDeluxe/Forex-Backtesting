"""Composite signal S_t in {-1, 0, +1} (Eq. 14)."""

import pandas as pd

from strategy.indicators import compute_adaptive_theta


def generate_signal(
    df: pd.DataFrame,
    theta: float | pd.Series | None = None,
    theta_window_bars: int = 500,
    theta_multiplier: float = 1.0,
    adx_ceiling: float | None = None,
    strict_adx_decay: bool = False,
) -> pd.DataFrame:
    """Evaluate the four joint conditions of Eq. 14 and emit S_t.

    `theta`: fixed scalar, a precomputed Series, or None (default) to use the
    adaptive rolling-std threshold from `compute_adaptive_theta`.
    `adx_ceiling`: not part of the paper's Eq. 14 — an optional extra filter
    (ADX_t < ceiling) being explored because real-data regime decomposition
    showed the paper's own trending-regime condition still lets through
    genuinely strong (>=25) trends, which is exactly the "fade a live trend"
    risk the paper's Foundation 3 warns about.
    `strict_adx_decay`: Remark 1 in the paper — Eq. 14 uses the weak
    condition dADX_t <= 0 ("not increasing"). The paper explicitly flags the
    strict version dADX_t < 0 ("actually decreasing") as a cleaner exhaustion
    signal, at the cost of fewer trades, and leaves the choice as an open
    empirical question. False (default) reproduces Eq. 14 exactly.
    """
    df = df.copy()
    if theta is None:
        theta = compute_adaptive_theta(df, theta_window_bars, theta_multiplier)
    df["theta"] = theta

    cond_adx_elevated = df["adx"] > df["adx_mean"]
    cond_adx_decaying = df["delta_adx"] < 0 if strict_adx_decay else df["delta_adx"] <= 0
    cond_adx_ceiling = df["adx"] < adx_ceiling if adx_ceiling is not None else True

    cond_at_high = df["close"] >= df["prev_high"]
    cond_above_vwap = df["deviation"] > df["theta"]

    cond_at_low = df["close"] <= df["prev_low"]
    cond_below_vwap = df["deviation"] < -df["theta"]

    short_mask = cond_at_high & cond_above_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling
    long_mask = cond_at_low & cond_below_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling

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
    adx_ceiling: float | None = None,
    strict_adx_decay: bool = False,
    session_start_hour: int | None = None,
    session_end_hour: int | None = None,
) -> pd.DataFrame:
    """`session_start_hour`/`session_end_hour` (both UTC, e.g. 7/17 for the
    paper's London-session option): if given, bars outside that window are
    dropped and the session boundary is pinned to `session_start_hour`,
    overriding `reset_hour`. Leave both None for the 24h rolling session.
    """
    from strategy.indicators import (
        compute_adx,
        compute_prev_session_extremes,
        compute_regime_filter,
        compute_vwap_and_deviation,
        filter_session_window,
    )

    if session_start_hour is not None and session_end_hour is not None:
        df = filter_session_window(df, session_start_hour, session_end_hour)
        reset_hour = session_start_hour

    out = compute_vwap_and_deviation(df, reset_hour=reset_hour)
    out = compute_prev_session_extremes(out)
    out = compute_adx(out, n=adx_n)
    out = compute_regime_filter(out, adx_window=adx_window)
    out = generate_signal(
        out, theta_window_bars=theta_window_bars, theta_multiplier=theta_multiplier,
        adx_ceiling=adx_ceiling, strict_adx_decay=strict_adx_decay,
    )
    return out
