"""Data fetch for asia_ote - EURUSD (Dukascopy, via combined_strategy.data,
same source/convention as gold_smc_htf_ltf and cls_practical) at whatever
timeframes the module needs: M15 for the Asia-range/entry mechanics, D1
for monthly pivot points, H1/H4 optionally for the trend-strength
direction filter (reuses gold_smc_htf_ltf.trend, timeframe-agnostic)."""

import pandas as pd

from combined_strategy.data import fetch_timeframe


def _fetch(key: str, timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe(key, timeframe, start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def fetch_eurusd_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("EURUSD", "M15", start, end, force_refresh)


def fetch_eurusd_h1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("EURUSD", "H1", start, end, force_refresh)


def fetch_eurusd_h4(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("EURUSD", "H4", start, end, force_refresh)


def fetch_eurusd_d1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch("EURUSD", "D1", start, end, force_refresh)
