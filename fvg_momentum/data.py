"""Data fetch for the Multi-Asset A/A+ Momentum Fair Value Gap strategy
rebuild (see scripts/research_fvg_momentum.py) - 5-minute entry timeframe +
1-hour structural timeframe, for XAUUSD, EURUSD, GBPUSD, USDJPY.

Source paper (Bindra 2025, "Multi-Asset A/A+ Momentum Fair Value Gap
Strategy") uses HistData 1-minute ASCII files, resampled internally to 5m/1h.
No local HistData access here - real Dukascopy OHLCV via the same
dukascopy_python bridge combined_strategy/data.py and strategy/real_data.py
already use elsewhere in this repo is used instead, a disclosed data-source
substitution like every other paper rebuild in this project. XAUUSD maps to
Dukascopy's XAU/USD spot instrument (combined_strategy.data.INSTRUMENTS
already has this as "GOLD" - same feed asian_range_breakout/data.py uses)."""

from pathlib import Path

import dukascopy_python
import pandas as pd

from combined_strategy.data import INSTRUMENTS, OFFER_SIDE, fetch_timeframe

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "fvg_momentum"

PAIRS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
_KEY_BY_PAIR = {"XAUUSD": "GOLD", "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY"}

# Pip size per instrument. EURUSD/GBPUSD/USDJPY follow standard FX convention.
# XAUUSD: the source paper applies the SAME 9-pip stop/target grid to Gold as
# to the FX pairs without ever defining what a "pip" means for Gold - a real
# ambiguity, not resolved by the source. Disclosed assumption here: 1 pip =
# $0.01 (matches the paper's own JPY-style 2-decimal convention), i.e. a
# 9-pip XAUUSD stop = $0.09 - deliberately kept literal rather than
# "corrected" to a more realistic Gold pip size, so the rebuild tests the
# paper's own stated rule, not a guess at what it "should" have said. If this
# turns out absurdly tight for Gold's real volatility, that itself is a
# finding worth reporting, not a bug to silently fix.
PIP_SIZE = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "XAUUSD": 0.01}


def _cache_path(pair: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp) -> Path:
    return CACHE_DIR / f"{pair}_{timeframe}_{start.date()}_{end.date()}.parquet"


def fetch_m5(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    key = _KEY_BY_PAIR[pair]
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = _cache_path(pair, "M5", start_ts, end_ts)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    df = dukascopy_python.fetch(
        INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index.name = "timestamp"
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_h1(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    key = _KEY_BY_PAIR[pair]
    return fetch_timeframe(key, "H1", start, end, force_refresh=force_refresh)
