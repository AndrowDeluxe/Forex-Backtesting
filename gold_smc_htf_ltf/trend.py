"""Trend-direction indicators for the Continuation strategy's trend filter
(chat 2026-08-14): "BOS ist der weitere Bruch eines Swing Highs/Lows in die
trendende Richtung" - a structural break only counts as a BOS (continuation
signal) if it agrees with an independently-computed trend direction, not
just "the second break in a row" (structure.py's original, cruder rule).

Timeframe-agnostic: each function takes whatever OHLC frame it's given -
the caller decides the timeframe (the user's own suggestion is to run the
trend gauge on M15/M30 while structure/BOS still comes from H4/H1, tested
as a swept parameter in the continuation research script, not hardcoded
here).

Each function returns an integer Series: 1 bullish, -1 bearish, 0 (only
adx_di) no-clear-trend."""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx


def trend_ema_cross(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    return pd.Series(np.where(ema_fast > ema_slow, 1, -1), index=df.index)


def trend_adx_di(df: pd.DataFrame, n: int = 14, adx_min: float = 20.0) -> pd.Series:
    """No-clear-trend (0) whenever ADX is below `adx_min` - unlike
    trend_ema_cross/trend_donchian, this can withhold an opinion."""
    d = compute_adx(df, n=n)
    direction = np.where(d["plus_di"] > d["minus_di"], 1, -1)
    trend = np.where(d["adx"] >= adx_min, direction, 0)
    return pd.Series(trend, index=df.index)


def trend_donchian(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Close vs. the midpoint of the trailing `window`-bar Donchian
    (high/low) channel."""
    upper = df["high"].rolling(window).max()
    lower = df["low"].rolling(window).min()
    mid = (upper + lower) / 2
    return pd.Series(np.where(df["close"] > mid, 1, -1), index=df.index)


def trend_ema_adx_combo(df: pd.DataFrame, fast: int = 20, slow: int = 50, adx_n: int = 14, adx_min: float = 20.0) -> pd.Series:
    """Direction from EMA(fast)/EMA(slow) (trend_ema_cross's own, smoother
    read - not adx_di's +DI/-DI comparison), STRENGTH-gated by ADX: 0
    (withhold opinion) whenever ADX < adx_min (chat 2026-08-20: "kannst du
    ADX und Ema kombinieren um Trend und Staerke zu bestimmen"). Isolates
    a specific hypothesis about why trend_adx_di outperformed trend_ema_
    cross/trend_donchian in the continuation trend-indicator sweep: is it
    the DI-based direction itself, or just the ability to say "no clear
    trend" that ema_cross/donchian lack (both always pick a side)? This
    keeps ema_cross's direction but adds adx_di's own selectivity."""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    direction = np.where(ema_fast > ema_slow, 1, -1)
    adx = compute_adx(df, n=adx_n)["adx"].to_numpy()
    trend = np.where(adx >= adx_min, direction, 0)
    return pd.Series(trend, index=df.index)


TREND_INDICATORS = {
    "ema_cross": trend_ema_cross,
    "adx_di": trend_adx_di,
    "donchian": trend_donchian,
    "ema_adx_combo": trend_ema_adx_combo,
}
