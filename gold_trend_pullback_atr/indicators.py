"""Bollinger Bands and MACD - the two indicators from the "Top-Tipps von
Tradern" article (see chat, 2026-08-13) not already available elsewhere in
this repo. RSI is reused as-is from checklist_strategy.indicators.rsi
(Wilder RSI), session-time gating from checklist_strategy.indicators.
compute_session_ok - no need to duplicate either here.
"""

import pandas as pd


def bollinger_bands(close: pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Standard Bollinger Bands: `window`-period SMA +/- k std deviations.
    Returns columns: mid, upper, lower."""
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std}, index=close.index)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Standard MACD: EMA(fast) - EMA(slow), plus its EMA(signal) signal line
    and the histogram (macd - signal_line). Returns columns: macd, signal_line, histogram."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {"macd": macd_line, "signal_line": signal_line, "histogram": macd_line - signal_line},
        index=close.index,
    )
