"""Data for the NY-Open Opening-Range-Breakout strategy - thin wrapper
around combined_strategy.data.fetch_timeframe (same Dukascopy feed already
used by orb_strategy/ and others). Index converted to America/New_York local
time via zoneinfo (proper DST handling, not a fixed UTC offset) since the
range anchor (09:30 NY cash open) and the session close (16:00 NY) are both
defined in NY local time - a fixed UTC-hour window would drift by an hour
during the few weeks each year where US and EU daylight-saving transitions
don't align (see auction_playbook/indicators.py's NY_SESSION for the
anti-pattern this avoids).

Instrument-parametrized (not just SP500): NASDAQ and US30 get tested
alongside SP500 (see knowledge/projects/ny-open-orb-sp500.md), all three via
the same Dukascopy CFD feed already registered in combined_strategy/data.py.
VIX is a genuine Dukascopy instrument too (INSTRUMENT_IDX_AMERICA_VOL_IDX_USD,
verified against known VIX levels) - no external yfinance/FRED dependency
needed for the regime filter.
"""

import time

import pandas as pd

from combined_strategy.data import fetch_timeframe

INSTRUMENTS = ("SP500", "NASDAQ", "US30")

# dukascopy_python's own streaming fetch occasionally raises a bare
# `KeyError: 0` (or, once observed, a `TypeError` comparing a str to a
# float) deep inside its `_stream()` cursor-tracking - intermittent, not
# tied to one instrument/timeframe/range (seen on SP500 M5 after many prior
# successful identical calls, and on US30/NASDAQ M5). Reads as flaky
# upstream streaming, not a deterministic data gap. A long M1/M5 request
# spanning many years fails more often (more internal pagination steps =
# more chances to hit it), so chunking by year both reduces the odds per
# call AND lets `_fetch_with_retry` retry just the one bad year instead of
# the whole multi-year request.
_CHUNKED_TIMEFRAMES = {"M1", "M5"}


def _fetch_with_retry(instrument: str, timeframe: str, start: str, end: str, force_refresh: bool, attempts: int = 4) -> pd.DataFrame:
    last_error = None
    for attempt in range(attempts):
        try:
            return fetch_timeframe(instrument, timeframe, start, end, force_refresh=force_refresh or attempt > 0)
        except Exception as exc:  # noqa: BLE001 - genuinely any dukascopy_python internal failure should trigger a retry here
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise last_error


def _fetch_chunked_by_year(instrument: str, timeframe: str, start: str, end: str, force_refresh: bool) -> pd.DataFrame:
    """Anchors chunk boundaries on `start` itself (start, start+1y, start+2y,
    ...), not a calendar year start - reproduces the exact boundary pattern
    verified to avoid the pagination bug (e.g. 2016-07-28..2017-07-28..., not
    an arbitrary 2017-01-01 cut, which was observed to still trip it)."""
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    bounds = [start_ts]
    cursor = start_ts
    while cursor + pd.DateOffset(years=1) < end_ts:
        cursor = cursor + pd.DateOffset(years=1)
        bounds.append(cursor)
    bounds.append(end_ts)

    parts = [
        _fetch_with_retry(instrument, timeframe, bounds[i].strftime("%Y-%m-%d"), bounds[i + 1].strftime("%Y-%m-%d"), force_refresh)
        for i in range(len(bounds) - 1)
    ]
    combined = pd.concat(parts).sort_index()
    return combined[~combined.index.duplicated()]  # consecutive chunks share their boundary bar (end[i] == start[i+1])


def _fetch(instrument: str, timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if timeframe in _CHUNKED_TIMEFRAMES:
        df = _fetch_chunked_by_year(instrument, timeframe, start, end, force_refresh)
    else:
        df = _fetch_with_retry(instrument, timeframe, start, end, force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("America/New_York")
    return df


def fetch_m1(instrument: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch(instrument, "M1", start, end, force_refresh)


def fetch_m5(instrument: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch(instrument, "M5", start, end, force_refresh)


def fetch_m15(instrument: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _fetch(instrument, "M15", start, end, force_refresh)


def fetch_vix_daily(start: str, end: str, force_refresh: bool = False) -> pd.Series:
    """Daily VIX close, NY-local dates (normalized) - a regime filter looks
    at "where was VIX as of yesterday's close", not intraday VIX ticks."""
    df = _fetch("VIX", "D1", start, end, force_refresh)
    out = df["close"]
    out.index = out.index.normalize()
    return out


# Backwards-compatible SP500-only aliases (Stage 1-3 scripts use these).
def fetch_sp500_m5(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return fetch_m5("SP500", start, end, force_refresh)


def fetch_sp500_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return fetch_m15("SP500", start, end, force_refresh)
