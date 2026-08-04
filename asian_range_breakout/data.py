"""Gold M15 data for the Asian-Range Breakout strategy - thin wrapper around
combined_strategy.data.fetch_timeframe (same Dukascopy XAUUSD feed already
used elsewhere in this repo). Columns lower-cased to match this package's/
strategy.indicators' convention, index converted to America/New_York local
time (proper DST handling via zoneinfo, not a fixed UTC offset) since the
source strategy's session/exit times are explicitly defined in NY local
time (see Gold_Asian_Breakout_Strategy.txt)."""

import pandas as pd

from combined_strategy.data import fetch_timeframe


def fetch_gold_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe("GOLD", "M15", start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("America/New_York")
    return df
