"""Gold data at every timeframe this package's strategies use - same
Dukascopy XAUUSD feed and NY-local tz convention as the rest of this
repo's gold packages."""

import pandas as pd

from combined_strategy.data import fetch_timeframe


def _fetch(timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe("GOLD", timeframe, start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("America/New_York")
    return df


def fetch_gold_m1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("M1", start, end, force_refresh)


def fetch_gold_m5(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("M5", start, end, force_refresh)


def fetch_gold_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("M15", start, end, force_refresh)


def fetch_gold_m30(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("M30", start, end, force_refresh)


def fetch_gold_h1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("H1", start, end, force_refresh)


def fetch_gold_h4(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("H4", start, end, force_refresh)


def fetch_gold_d1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("D1", start, end, force_refresh)


def fetch_gold_w1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("W1", start, end, force_refresh)
