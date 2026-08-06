"""Daily US Dollar Index (DXY, ticker DX-Y.NYB) via yfinance - same pattern
as vix.py. Used to test the "151 Trading Strategies" cross-asset-confirmation
idea (paper151 Gold tab, 2026-08-06): Gold is USD-denominated, so a trending
dollar is a structural head-/tailwind independent of Gold's own chart. Cached
to parquet like the rest of this package's data."""

from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "asian_range_breakout"


def fetch_dxy_daily(start: str, end: str, force_refresh: bool = False) -> pd.Series:
    path = CACHE_DIR / f"DXY_{start}_{end}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)["close"]

    df = yf.download("DX-Y.NYB", start=start, end=end, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    close = df["Close"].rename("close").dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close.index.name = "date"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    close.to_frame().to_parquet(path)
    return close
