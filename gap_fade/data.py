"""Data access for the Gap-Fade strategy: daily EUR/USD & GBP/USD bars via
the existing Dukascopy cache (see strategy/real_data.py). Reuses the same
cached parquet mechanism -- daily bars are just another `_INTERVAL_LABELS`
entry there (INTERVAL_DAY_1 -> "D1"), so no separate fetch/cache logic
needed here.
"""

import dukascopy_python

from strategy.real_data import fetch_pair_history

PAIRS = ["EURUSD", "GBPUSD"]


def fetch_daily(pair: str, start: str, end: str, force_refresh: bool = False):
    """Daily OHLCV bars for `pair`, Dukascopy's own daily-candle convention
    (i.e. its own trading-day boundary), cached to data_cache/."""
    if pair not in PAIRS:
        raise ValueError(f"gap_fade only covers {PAIRS}, got {pair}")
    return fetch_pair_history(
        pair, start, end, interval=dukascopy_python.INTERVAL_DAY_1, force_refresh=force_refresh
    )
