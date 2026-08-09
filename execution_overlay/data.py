"""Market data for the Execution-Overlay test: SPY 5-minute RTH bars (Yahoo
Finance via yfinance -- only ~60 days of history available for free, unlike
the paper's SPY 2007-2026 sample; see app_pages/execution_overlay_writeup.py
for the caveat) plus SPY daily bars (much deeper free history) to compute a
lookahead-free ATR(14) for the session bands.

`fetch_eurusd_5m`/`fetch_eurusd_daily` are the follow-up: same engine,
EUR/USD via the repo's existing Dukascopy cache (strategy/real_data.py),
which has real multi-year 5-minute depth -- no data-length caveat there.
"""

import dukascopy_python
import pandas as pd
import yfinance as yf

from strategy.real_data import fetch_pair_history


def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance sometimes returns a (Price, Ticker) MultiIndex -- collapse it,
    same fix as ema_strategy/data.py::_to_ohlc."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()


def fetch_spy_5m_rth() -> pd.DataFrame:
    """SPY 5-minute bars, regular trading hours, ~last 60 days (yfinance's
    free-tier cap for 5m data). Already RTH-only and America/New_York-
    localised as returned by Yahoo -- no session filtering needed."""
    df = yf.download("SPY", period="60d", interval="5m", progress=False, auto_adjust=False)
    return _flatten_yf_columns(df)


def fetch_spy_daily(period: str = "2y") -> pd.DataFrame:
    """SPY daily bars, deep history (no 60-day cap on daily) -- used only to
    compute ATR(14) with proper warmup, so none of the scarce 5m intraday
    history is spent on ATR burn-in."""
    df = yf.download("SPY", period=period, interval="1d", progress=False, auto_adjust=False)
    return _flatten_yf_columns(df)


def fetch_eurusd_5m(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """EUR/USD 5-minute bars via the existing Dukascopy cache. FX has no
    session open in the SPY-cash sense (24h market); the research script
    treats each Dukascopy calendar day as one "session" (same convention
    as gap_fade/), which means Sunday's few-hour partial reopen forms its
    own short session unless filtered out by the caller."""
    return fetch_pair_history(
        "EURUSD", start, end, interval=dukascopy_python.INTERVAL_MIN_5, force_refresh=force_refresh
    )


def fetch_eurusd_daily(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """EUR/USD daily bars for the ATR(14) input -- same Dukascopy D1 series
    gap_fade/ uses, including its Sunday-reopen sliver bar (see
    gap_fade/engine.py's docstring); the research script filters it out
    before computing ATR here too."""
    return fetch_pair_history(
        "EURUSD", start, end, interval=dukascopy_python.INTERVAL_DAY_1, force_refresh=force_refresh
    )
