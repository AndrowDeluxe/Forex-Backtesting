"""Indicators for the 4-indicator checklist strategy.

Best-effort reconstruction from each indicator's public TradingView settings
dialog (screenshots), NOT verified against Pine Script source - flagged
wherever a specific formula choice is an assumption rather than a confirmed
fact, so results can be sanity-checked against the live chart before trust.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx, compute_atr, wilder_smooth


def nadaraya_watson_envelope(
    close: pd.Series, h: float = 8.0, mult: float = 3.0, window: int = 500
) -> pd.DataFrame:
    """Causal (non-repainting) Nadaraya-Watson envelope: a Gaussian-kernel-
    weighted moving average (bandwidth `h`), using only the current and past
    `window` bars at each point (no centered/future-aware kernel regression
    - that variant is the *repainting* mode and cannot be legitimately
    backtested, see the LuxAlgo indicator's own repainting toggle).

    `window` (bars of history the kernel looks back over) isn't one of the
    two numbers given for this indicator (h=8, mult=3) - LuxAlgo's default is
    500, kept here as a reasonable assumption; it mainly controls how far
    back the average-absolute-error band width is estimated from, not the
    smoothing responsiveness (that's `h`).

    Returns a DataFrame with columns: mid, upper, lower.
    """
    price = close.to_numpy(dtype=float)
    n = len(price)
    L = min(window, n)

    lags = np.arange(L)
    kernel = np.exp(-(lags**2) / (2 * h**2))

    numerator = np.convolve(price, kernel, mode="full")[:n]
    kernel_cumsum = np.cumsum(kernel)
    denom_idx = np.minimum(np.arange(n), L - 1)
    denominator = kernel_cumsum[denom_idx]

    mid = numerator / denominator

    abs_resid = np.abs(price - mid)
    resid_series = pd.Series(abs_resid)
    mae = resid_series.rolling(window=L, min_periods=1).mean().to_numpy() * mult

    return pd.DataFrame(
        {"mid": mid, "upper": mid + mae, "lower": mid - mae}, index=close.index
    )


def rsi(close: pd.Series, length: int) -> pd.Series:
    """Wilder RSI (TradingView default: RMA-smoothed gains/losses)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = wilder_smooth(gain, length)
    avg_loss = wilder_smooth(loss, length)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        out = 100 - 100 / (1 + rs)
    # avg_loss == 0 (pure uptrend over the window) -> RSI saturates at 100.
    out = out.where(avg_loss != 0, 100.0)
    return out


def rsi_multi_length(close: pd.Series, min_length: int = 10, max_length: int = 20) -> pd.Series:
    """LuxAlgo 'RSI Multi Length': average of RSI(len) for every integer
    length from `min_length` to `max_length` inclusive."""
    lengths = range(min_length, max_length + 1)
    rsis = pd.concat([rsi(close, n) for n in lengths], axis=1)
    return rsis.mean(axis=1)


def rsi_with_ma(close: pd.Series, rsi_length: int = 14, ma_length: int = 14) -> pd.DataFrame:
    """Standard RSI + its SMA (TradingView's built-in 'RSI' indicator's
    Moving Average overlay). Returns columns: rsi, rsi_ma."""
    r = rsi(close, rsi_length)
    ma = r.rolling(window=ma_length, min_periods=ma_length).mean()
    return pd.DataFrame({"rsi": r, "rsi_ma": ma}, index=close.index)


def compute_regime_ok(
    df: pd.DataFrame,
    adx_n: int = 14,
    adx_threshold: float = 25.0,
    vol_atr_n: int = 14,
    vol_lookback: int = 200,
    require_not_trending: bool = True,
    require_volatile: bool = True,
) -> pd.Series:
    """"Volatile but not strongly trending": ADX(adx_n) below `adx_threshold`
    (not a persistent directional trend - the regime this envelope-fade
    style strategy should struggle least in) AND/OR ATR(vol_atr_n) above its
    own rolling median over `vol_lookback` bars (an active, not a dead-quiet,
    market - there needs to be enough range for the envelope/RSI conditions
    to mean anything). Both computed on the same timeframe as `df`.

    `require_not_trending`/`require_volatile`: each can be switched off to
    test the two halves of the filter individually - e.g. the combined
    filter alone can be too restrictive to sample from (see MEMORY), and
    the trend half alone is a natural first thing to relax to.
    """
    conditions = []
    if require_not_trending:
        adx_val = compute_adx(df, n=adx_n)["adx"]
        conditions.append(adx_val < adx_threshold)
    if require_volatile:
        atr_n = compute_atr(df, n=vol_atr_n)
        vol_median = atr_n.rolling(window=vol_lookback, min_periods=vol_lookback // 2).median()
        conditions.append(atr_n > vol_median)

    if not conditions:
        return pd.Series(True, index=df.index)
    out = conditions[0]
    for cond in conditions[1:]:
        out = out & cond
    return out.fillna(False)
