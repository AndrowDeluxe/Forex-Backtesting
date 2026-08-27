"""Gold M1 data - same Dukascopy XAUUSD feed and NY-local tz convention as
asian_range_breakout/data.py::fetch_gold_m15, just M1 instead of M15."""

import pandas as pd

from combined_strategy.data import fetch_timeframe


def fetch_gold_m1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe("GOLD", "M1", start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("America/New_York")
    return df
