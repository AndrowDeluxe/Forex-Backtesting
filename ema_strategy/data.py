"""Market data for the EMA S/R strategy: live Yahoo Finance fetch (via
`yfinance`), OHLC resampling, and multi-timeframe bias/ADX attachment.

Ticker choice:
  - EUR/USD: EURUSD=X  (trades near-24h)
  - Gold:    GC=F       (Comex future; Yahoo has no 24h spot series)
  - S&P 500: ES=F       (E-mini future instead of the ^GSPC cash index,
                         which only quotes during 9:30-16:00 ET and would
                         leave gaps/artifacts when resampled to fixed 4h bars)

Futures prices carry roll gaps (jumps at contract rollover); FX data has no
real traded volume. These are accepted, documented limitations of freely
available data, not bugs.
"""

import numpy as np
import pandas as pd
import yfinance as yf

from ema_strategy.indicators import adx, double_ema

ASSETS = {
    "EURUSD": "EURUSD=X",
    "GOLD": "GC=F",
    "SP500": "ES=F",
}


def _to_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Yahoo sometimes returns a MultiIndex (Price, Ticker) column format --
    collapse it to plain OHLC columns."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].copy()
    if df.index.tz is not None:
        # Yahoo returns tz-aware timestamps whose UTC offset changes across
        # DST transitions; normalise to naive UTC for consistent sorting/merging.
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    df.index.name = "Date"
    return df.dropna()


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in df.columns:
        agg["Volume"] = "sum"
    return df.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["Close"])


def fetch_h4_and_daily(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch hourly (resampled to H4, ~730d — Yahoo's hourly-data cap) and
    native daily (~15y) OHLC for `ticker`."""
    h1 = yf.download(ticker, period="730d", interval="1h", progress=False)
    h4 = resample_ohlc(_to_ohlc(h1), "4h")

    d1 = yf.download(ticker, period="15y", interval="1d", progress=False)
    daily = _to_ohlc(d1)

    return h4, daily


def attach_htf_bias(h4: pd.DataFrame, htf: pd.DataFrame, prefix: str,
                     length: int, smooth: int, slope_lookback: int = 3) -> pd.DataFrame:
    """No-lookahead merge of a higher-timeframe EMA bias onto `h4` (only
    fully closed HTF bars are used)."""
    htf = htf.copy()
    htf[f"{prefix}_ema"] = double_ema(htf["Close"], length, smooth)
    htf[f"{prefix}_bias"] = np.where(htf["Close"] > htf[f"{prefix}_ema"], 1, -1)
    htf[f"{prefix}_slope"] = np.sign(htf[f"{prefix}_ema"].diff(slope_lookback))
    src = htf[[f"{prefix}_ema", f"{prefix}_bias", f"{prefix}_slope"]].reset_index()
    src.columns = ["Date", f"{prefix}_ema", f"{prefix}_bias", f"{prefix}_slope"]

    left = h4.reset_index().rename(columns={h4.index.name or "index": "Date"})
    merged = pd.merge_asof(
        left.sort_values("Date"), src.sort_values("Date"),
        on="Date", direction="backward", allow_exact_matches=True,
    )
    return merged.set_index("Date")


def attach_adx(target: pd.DataFrame, htf: pd.DataFrame, prefix: str, period: int = 14) -> pd.DataFrame:
    """Same no-lookahead merge_asof pattern as attach_htf_bias, for ADX(period)
    computed on `htf` (e.g. daily) and merged onto `target` (trigger timeframe)."""
    htf = htf.copy()
    htf[f"{prefix}_adx"] = adx(htf, period)
    src = htf[[f"{prefix}_adx"]].reset_index()
    src.columns = ["Date", f"{prefix}_adx"]

    left = target.reset_index().rename(columns={target.index.name or "index": "Date"})
    merged = pd.merge_asof(
        left.sort_values("Date"), src.sort_values("Date"),
        on="Date", direction="backward", allow_exact_matches=True,
    )
    return merged.set_index("Date")
