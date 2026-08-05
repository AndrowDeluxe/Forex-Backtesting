"""Daily OHLC data for the Triple Moving Average strategy - reuses
combined_strategy's Dukascopy D1 feed (same instruments/cache as the rest
of this repo) rather than fetching Yahoo Finance S&P 500 data fresh.

Difference from the paper: the paper used 1997-01-01 to 2020-01-01 Yahoo
Finance data. Dukascopy's depth here only reaches back to ~2016 (see
combined_strategy/data.py), so this module's usable window is ~2016-2026,
not the paper's ~23-year span - flagged explicitly, not silently swapped.
"""

from combined_strategy.data import INSTRUMENTS, fetch_timeframe


def fetch_daily(key: str, start: str, end: str, force_refresh: bool = False):
    return fetch_timeframe(key, "D1", start, end, force_refresh)
