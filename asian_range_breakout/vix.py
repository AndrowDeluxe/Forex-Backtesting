"""Daily VIX close (^VIX, CBOE) via yfinance - same data source already used
by ema_strategy/data.py elsewhere in this repo. Cached to parquet like the
rest of this package's data. Used as a same-day regime filter: a trade's
Asian-range window (21:00-01:00 NY) starts AFTER that calendar day's NYSE
session (and therefore that day's VIX close) is already known - no
lookahead in using it."""

from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "asian_range_breakout"


def fetch_vix_daily(start: str, end: str, force_refresh: bool = False) -> pd.Series:
    path = CACHE_DIR / f"VIX_{start}_{end}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)["close"]

    df = yf.download("^VIX", start=start, end=end, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    close = df["Close"].rename("close").dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close.index.name = "date"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    close.to_frame().to_parquet(path)
    return close
