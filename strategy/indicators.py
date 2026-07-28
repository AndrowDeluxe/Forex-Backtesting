"""Core indicator layer: session VWAP (Eq. 1-3), previous-session extremes
(Sec. 4.3), Wilder's ADX (Eq. 4-10), and the regime filter (Eq. 11-13).

Deviations from the paper's Appendix A reference code are noted inline where
they fix a bug or close a look-ahead gap; each is deliberate, not a rewrite
for style.
"""

import numpy as np
import pandas as pd


def assign_sessions(index: pd.DatetimeIndex, reset_hour: int = 22) -> pd.Series:
    """Session id per bar, rolling over daily at `reset_hour` UTC (default: NY ~17:00 local)."""
    shifted = index - pd.Timedelta(hours=reset_hour)
    return pd.Series(shifted.date, index=index)


def filter_session_window(df: pd.DataFrame, start_hour: int, end_hour: int) -> pd.DataFrame:
    """Restrict bars to a bounded intraday window (Sec. 6.1's named London
    07:00-17:00 / NY 13:00-22:00 GMT options), instead of a 24h rolling VWAP.

    Bars outside [start_hour, end_hour) UTC are dropped entirely, so each
    remaining calendar day is exactly one session when paired with
    `reset_hour=start_hour` downstream — VWAP resets at window open and
    prior-session extremes are the prior day's *window* high/low, not the
    full 24h range.
    """
    hour = df.index.hour
    return df[(hour >= start_hour) & (hour < end_hour)].copy()


def compute_vwap_and_deviation(df: pd.DataFrame, reset_hour: int = 22) -> pd.DataFrame:
    df = df.copy()
    df["session"] = assign_sessions(df.index, reset_hour)

    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = typical_price * df["volume"]

    cum_pv = pv.groupby(df["session"]).cumsum()
    cum_vol = df["volume"].groupby(df["session"]).cumsum()

    df["vwap"] = cum_pv / cum_vol
    df["deviation"] = (df["close"] - df["vwap"]) / df["vwap"]
    return df


def compute_prev_session_extremes(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the *prior* session's high/low to every bar of the current session.

    Uses `df["session"]` set by compute_vwap_and_deviation; sessions are
    ordered by first appearance, so this is robust to reset_hour != midnight.
    """
    df = df.copy()
    session_hi_lo = df.groupby("session").agg(session_high=("high", "max"), session_low=("low", "min"))
    session_hi_lo = session_hi_lo.sort_index()
    session_hi_lo["prev_high"] = session_hi_lo["session_high"].shift(1)
    session_hi_lo["prev_low"] = session_hi_lo["session_low"].shift(1)

    df["prev_high"] = df["session"].map(session_hi_lo["prev_high"])
    df["prev_low"] = df["session"].map(session_hi_lo["prev_low"])
    return df


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder smoothing (Eq. 6/7): X_t = ((n-1) X_{t-1} + x_t) / n.

    The paper's Appendix A listing seeds the recursion with
    `sum(first n values)` instead of their *mean*, which inflates the
    entire series by a persistent, slowly-decaying transient (the (n-1)/n
    recursion does not erase an n-fold seed error within any bounded
    horizon relevant here). This implementation seeds with the mean, which
    is the standard Wilder (1978) convention and what "First ATR = SMA of
    first n TR values" actually means.
    """
    values = series.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n <= period:
        return pd.Series(out, index=series.index)
    out[period] = np.nanmean(values[1 : period + 1])
    for i in range(period + 1, n):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return pd.Series(out, index=series.index)


def compute_adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]

    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1
    ).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr = _wilder_smooth(tr, n)
    s_plus = _wilder_smooth(plus_dm, n)
    s_minus = _wilder_smooth(minus_dm, n)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100 * s_plus / atr
        minus_di = 100 * s_minus / atr
        di_sum = plus_di + minus_di
        dx = 100 * (plus_di - minus_di).abs() / di_sum.where(di_sum != 0)
    dx = dx.fillna(0.0)

    adx = _wilder_smooth(dx, n)

    df["atr"] = atr
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    df["adx"] = adx
    return df


def compute_regime_filter(df: pd.DataFrame, adx_window: int = 20) -> pd.DataFrame:
    df = df.copy()
    df["adx_mean"] = df["adx"].rolling(window=adx_window).mean()
    df["delta_adx"] = df["adx"].diff()
    return df


def compute_intraday_window_extremes(df: pd.DataFrame, window_start_hour: float, window_end_hour: float) -> pd.DataFrame:
    """Attach the running high/low reached *within* a same-day intraday
    window (e.g. a CLS settlement cutoff window, 06:00-07:00 UTC) to every
    bar of that day, frozen at its final value once the window closes.

    Unlike `compute_prev_session_extremes` (previous *session's* extreme,
    used cross-day), this is a same-day, sub-session window: bars before
    the window are NaN (nothing to reference yet), bars during it see the
    running max/min so far, and bars after it see the window's final,
    frozen high/low - exactly what a post-cutoff entry signal needs.
    """
    df = df.copy()
    hour = df.index.hour + df.index.minute / 60.0
    date = pd.Series(df.index.date, index=df.index)
    in_window = (hour >= window_start_hour) & (hour < window_end_hour)

    high_masked = df["high"].where(in_window)
    low_masked = df["low"].where(in_window)

    window_high = high_masked.groupby(date).cummax().groupby(date).ffill()
    window_low = low_masked.groupby(date).cummin().groupby(date).ffill()

    df["window_high"] = window_high
    df["window_low"] = window_low
    return df


def compute_adaptive_theta(df: pd.DataFrame, window_bars: int, multiplier: float = 1.0) -> pd.Series:
    """Rolling std of D_t as a time-varying threshold (Sec. 6.2: 'theta as a
    function of the pair's intraday volatility regime'). Uses only current
    and past bars at each point, so it introduces no look-ahead.
    """
    return df["deviation"].rolling(window=window_bars, min_periods=window_bars // 2).std() * multiplier
