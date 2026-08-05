"""Gold M15 data for the Asian-Range Breakout strategy - thin wrapper around
combined_strategy.data.fetch_timeframe (same Dukascopy XAUUSD feed already
used elsewhere in this repo). Columns lower-cased to match this package's/
strategy.indicators' convention, index converted to America/New_York local
time (proper DST handling via zoneinfo, not a fixed UTC offset) since the
source strategy's session/exit times are explicitly defined in NY local
time (see Gold_Asian_Breakout_Strategy.txt).

fetch_gold_m15_live() is a SEPARATE function for the dashboard's "Live
Entry-Signal" tab only - Dukascopy's own data has a large, variable lag
(observed 2026-08-05: >10h behind real time even bypassing our own cache),
fine for the validated 10-year backtest (which never needs "now") but
useless for a live-ish display. yfinance's GC=F (Gold futures, same ticker
ema_strategy/data.py already uses) was ~19 min behind when checked the same
day - not committed anywhere, only used for this one illustrative view."""

import pandas as pd
import yfinance as yf

from combined_strategy.data import fetch_timeframe


def fetch_gold_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_timeframe("GOLD", "M15", start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("America/New_York")
    return df


def fetch_gold_m15_live(period: str = "60d") -> pd.DataFrame:
    """Gold FUTURES (GC=F, not spot XAUUSD - can differ slightly from spot,
    e.g. cost-of-carry premium/discount, occasional contract-roll gaps) via
    yfinance, for the dashboard's live-ish display only - never used for the
    validated backtest, which stays on Dukascopy for methodological
    consistency with every finding on that page."""

    df = yf.download("GC=F", period=period, interval="15m", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    df.index = df.index.tz_convert("America/New_York")
    df.index.name = "timestamp"
    return df.dropna()
