"""EUR/USD M5 data (Dukascopy, Europe/Berlin local time) for the Pre-Settle
Range Breakout - user's own manual observation (2026-08-10): banks square
intraday liquidity in the 06:00-07:00 Berlin pre-settle window (same window
already documented in strategy/cls_advanced.py's CLS Advanced framework);
the resulting range's breakout after 07:00 is the trade.

Same dukascopy_python bridge combined_strategy/data.py and fvg_momentum/data.py
already use elsewhere in this repo, just at M5 and tz-converted to Berlin
(the CLS-relevant local session time, not UTC) instead of left in UTC.
"""

from pathlib import Path

import dukascopy_python
import pandas as pd

from combined_strategy.data import INSTRUMENTS, OFFER_SIDE

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "presettle_breakout"


def _cache_path(pair: str, start: pd.Timestamp, end: pd.Timestamp) -> Path:
    return CACHE_DIR / f"{pair}_M5_{start.date()}_{end.date()}.parquet"


def fetch_m5_berlin(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if pair not in INSTRUMENTS:
        raise ValueError(f"unknown pair {pair!r}, expected one of {list(INSTRUMENTS)}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = _cache_path(pair, start_ts, end_ts)
    if path.exists() and not force_refresh:
        df = pd.read_parquet(path)
    else:
        df = dukascopy_python.fetch(
            INSTRUMENTS[pair], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
            start_ts.to_pydatetime(), end_ts.to_pydatetime(),
        )
        df = df.sort_index()
        df.index.name = "timestamp"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)

    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df
