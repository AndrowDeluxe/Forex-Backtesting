"""Dukascopy data for the paper's actual named instruments (Futures: NASDAQ,
ES) - via the E-mini S&P 500 / Nasdaq-100 CFD proxies this repo already uses
elsewhere (`combined_strategy/data.py`), reused here as their own small
fetcher so `auction_playbook` stays self-contained.

**Data-quality tradeoff, disclosed rather than hidden**: unlike Binance,
Dukascopy reports one aggregate `volume` per bar - no taker buy/sell split,
so there is no genuine per-bar aggression signal available here the way
`data.py`'s Binance fetch gets one. `delta` here is instead the standard
OHLC-shape proxy - `((close-open)/(high-low)) * volume` - i.e. an inferred
guess from candle shape, not measured trade-side volume. This is exactly
the tradeoff the user chose to accept in order to match the paper's stated
Futures/NASDAQ/ES instruments rather than substitute a different, better-
instrumented asset class.

Also worth noting: Dukascopy's own "volume" for CFD/index instruments is
itself a broker-side (tick-derived) proxy, not real CME exchange volume -
a second-order caveat on top of the OHLC-shape delta proxy above.

Produces the same column shape as `data.py::fetch_klines` (open, high, low,
close, volume, delta) so `auction_playbook.signals.generate_playbook_trades`
runs unmodified regardless of which data source feeds it.
"""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka
import numpy as np
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache_futures"

INSTRUMENTS = {
    "SP500": duka.INSTRUMENT_IDX_AMERICA_E_SANDP_500,   # ES proxy
    "NASDAQ": duka.INSTRUMENT_IDX_AMERICA_E_NQ_100,      # NASDAQ/NQ proxy
}
_INTERVALS = {"M5": dukascopy_python.INTERVAL_MIN_5, "M15": dukascopy_python.INTERVAL_MIN_15}
OFFER_SIDE = dukascopy_python.OFFER_SIDE_BID


def _cache_path(symbol: str, interval: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{symbol}_{interval}_{start}_{end}.parquet"


def fetch_index_bars(symbol: str, interval: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if symbol not in INSTRUMENTS:
        raise ValueError(f"unknown symbol {symbol!r}, expected one of {list(INSTRUMENTS)}")
    if interval not in _INTERVALS:
        raise ValueError(f"unknown interval {interval!r}, expected one of {list(_INTERVALS)}")

    path = _cache_path(symbol, interval, start, end)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = dukascopy_python.fetch(
        INSTRUMENTS[symbol], _INTERVALS[interval], OFFER_SIDE, start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index.name = "timestamp"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    rng = (df["high"] - df["low"]).replace(0.0, np.nan)
    df["delta"] = ((df["close"] - df["open"]) / rng) * df["volume"]
    df["delta"] = df["delta"].fillna(0.0)

    out = df[["open", "high", "low", "close", "volume", "delta"]]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out
