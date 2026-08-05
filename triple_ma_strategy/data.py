"""Daily OHLC data for the Triple Moving Average strategy - reuses
combined_strategy's Dukascopy D1 feed (same instruments/cache as the rest
of this repo) rather than fetching Yahoo Finance S&P 500 data fresh, plus
Binance daily klines for BTC (same source as auction_playbook, the only
other crypto-aware module in this repo).

Difference from the paper: the paper used 1997-01-01 to 2020-01-01 Yahoo
Finance data. Dukascopy's depth here only reaches back to ~2016 (see
combined_strategy/data.py), so this module's usable window is ~2016-2026,
not the paper's ~23-year span - flagged explicitly, not silently swapped.
BTC has even less depth: Binance only lists BTCUSDT from 2017-08-17, so a
"2016-2026" request silently returns whatever Binance actually has, starting
later - not a bug, just a shorter available history for that one instrument.
"""

from auction_playbook.data import fetch_klines
from combined_strategy.data import INSTRUMENTS, fetch_timeframe

CRYPTO_SYMBOLS = {"BTC": "BTCUSDT"}
ALL_INSTRUMENTS = list(INSTRUMENTS) + list(CRYPTO_SYMBOLS)

_OHLCV_RENAME = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}


def fetch_daily(key: str, start: str, end: str, force_refresh: bool = False):
    if key in CRYPTO_SYMBOLS:
        df = fetch_klines(CRYPTO_SYMBOLS[key], "1d", start, end, force_refresh)
        return df.rename(columns=_OHLCV_RENAME)
    return fetch_timeframe(key, "D1", start, end, force_refresh)
