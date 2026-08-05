"""Triple EMA (TEMA) and Triple SMA (TSMA), per the paper's Eq. in Sec. 1:

TEMA = 3*EMA(p,n) - 3*EMA(EMA(p,n),n) + EMA(EMA(EMA(p,n),n),n)
TSMA = 3*SMA(p,n) - 3*SMA(SMA(p,n),n) + SMA(SMA(SMA(p,n),n),n)

Both are "triple" only in the sense of nesting the same n-period average
three times to cut lag vs. a plain n-period average - not the 20/30/50-day
"Three Triple" crossover in signals.py, which is a separate, second layer.
"""

import pandas as pd


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def tema(series: pd.Series, n: int) -> pd.Series:
    ema1 = ema(series, n)
    ema2 = ema(ema1, n)
    ema3 = ema(ema2, n)
    return 3 * ema1 - 3 * ema2 + ema3


def tsma(series: pd.Series, n: int) -> pd.Series:
    sma1 = sma(series, n)
    sma2 = sma(sma1, n)
    sma3 = sma(sma2, n)
    return 3 * sma1 - 3 * sma2 + sma3


def triple_ma(series: pd.Series, n: int, ma_type: str = "tema") -> pd.Series:
    if ma_type == "tema":
        return tema(series, n)
    if ma_type == "tsma":
        return tsma(series, n)
    raise ValueError(f"unknown ma_type {ma_type!r}, expected 'tema' or 'tsma'")
