"""EMA S/R strategy indicators: double-smoothed EMA and Wilder's ADX."""

import numpy as np
import pandas as pd


def double_ema(close: pd.Series, length: int = 50, smooth: int = 15) -> pd.Series:
    """EMA(length) on close, then EMA(smooth) on that EMA line itself
    ("length 50, smoothing 15")."""
    base = close.ewm(span=length, adjust=False).mean()
    smoothed = base.ewm(span=smooth, adjust=False).mean()
    return smoothed


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index (Wilder). Wilder smoothing is approximated
    via ewm(alpha=1/period), the same building block as double_ema."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_high, prev_low, prev_close = high.shift(1), low.shift(1), close.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    alpha = 1 / period
    smoothed_tr = tr.ewm(alpha=alpha, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(alpha=alpha, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(alpha=alpha, adjust=False).mean()

    plus_di = 100 * smoothed_plus_dm / smoothed_tr
    minus_di = 100 * smoothed_minus_dm / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=alpha, adjust=False).mean()
