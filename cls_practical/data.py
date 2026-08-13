"""Data fetch for the CLS Practical Playbook rebuild (cls_practical/) - see
scripts/research_cls_practical.py. Reuses presettle_breakout.data (EUR/USD
and the other FX majors, Dukascopy M5/M15, Berlin tz) and adds the one new
feed this strategy needs: BUND/USTBOND CFD prices, as the best freely
available intraday rates proxy (see engine.py module docstring for why this
is a LONG-END duration proxy, not the front-end/2Y signal the source
material actually describes - a disclosed data-source substitution, same
discipline as every other paper/playbook rebuild in this repo)."""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka
import pandas as pd

from combined_strategy.data import OFFER_SIDE, fetch_timeframe

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "cls_practical"

_RATE_INSTRUMENTS = {
    "BUND": duka.INSTRUMENT_BND_CFD_BUND_TR_EUR,      # ~10y German Bund future CFD
    "USTBOND": duka.INSTRUMENT_BND_CFD_USTBOND_TR_USD,  # ~15-25y US Treasury Bond future CFD
}


def fetch_rate_instrument_m5_berlin(key: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if key not in _RATE_INSTRUMENTS:
        raise ValueError(f"unknown rate instrument {key!r}, expected one of {list(_RATE_INSTRUMENTS)}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = CACHE_DIR / f"{key}_M5_{start_ts.date()}_{end_ts.date()}.parquet"
    if path.exists() and not force_refresh:
        df = pd.read_parquet(path)
    else:
        df = dukascopy_python.fetch(
            _RATE_INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
            start_ts.to_pydatetime(), end_ts.to_pydatetime(),
        )
        df = df.sort_index()
        df.index.name = "timestamp"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)

    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def fetch_major_m15_berlin(key: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """The 5 non-traded FX majors, for the cross-pair confirmation check
    (strategy.cls_advanced.compute_cross_confirmation) - M15 is plenty for a
    daily 06:00-09:00 move sign, no need for the traded pair's own M5
    precision here."""
    df = fetch_timeframe(key, "M15", start, end, force_refresh=force_refresh)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


_EURUSD_NATIVE_INTERVALS = {
    "M1": dukascopy_python.INTERVAL_MIN_1,
    "M5": dukascopy_python.INTERVAL_MIN_5,
    "M15": dukascopy_python.INTERVAL_MIN_15,
}


def fetch_eurusd_entry_tf_berlin(timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """EUR/USD at an arbitrary entry timeframe (Berlin tz, lowercase OHLC
    cols) for the fractal-trigger mechanics to run on. M1/M5/M15 are native
    Dukascopy intervals; Dukascopy has no M3 interval, so "M3" is built by
    resampling real M1 bars to 3-minute buckets (label=left, i.e. a bucket
    stamped 09:30 covers 09:30:00-09:32:59) - genuine M1 ticks, not a
    synthetic approximation, just re-bucketed."""
    if timeframe == "M3":
        m1 = fetch_eurusd_entry_tf_berlin("M1", start, end, force_refresh=force_refresh)
        resampled = m1.resample("3min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
        return resampled

    if timeframe not in _EURUSD_NATIVE_INTERVALS:
        raise ValueError(f"unknown timeframe {timeframe!r}, expected one of {list(_EURUSD_NATIVE_INTERVALS) + ['M3']}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = CACHE_DIR / f"EURUSD_{timeframe}_{start_ts.date()}_{end_ts.date()}.parquet"
    if path.exists() and not force_refresh:
        df = pd.read_parquet(path)
    else:
        from combined_strategy.data import INSTRUMENTS

        df = dukascopy_python.fetch(
            INSTRUMENTS["EURUSD"], _EURUSD_NATIVE_INTERVALS[timeframe], OFFER_SIDE,
            start_ts.to_pydatetime(), end_ts.to_pydatetime(),
        )
        df = df.sort_index()
        df.index.name = "timestamp"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)

    df.index = df.index.tz_convert("Europe/Berlin")
    return df
