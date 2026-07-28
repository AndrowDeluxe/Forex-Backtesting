"""Real historical FX data via Dukascopy (free ECN tick/bar feed).

Unlike `strategy/data.py` (synthetic), this pulls actual traded OHLCV bars.
Fetches are slow (~1-2 min per pair for 10 years of M15 bars) and hit an
external service, so results are cached to disk as parquet and never
re-fetched for a given (pair, interval, start, end) once cached.
"""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka_instruments
import pandas as pd

from strategy.data import PAIRS

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache"

_PAIR_TO_DUKASCOPY = {
    "EURUSD": duka_instruments.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka_instruments.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka_instruments.INSTRUMENT_FX_MAJORS_USD_JPY,
    "USDCHF": duka_instruments.INSTRUMENT_FX_MAJORS_USD_CHF,
    "AUDUSD": duka_instruments.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCAD": duka_instruments.INSTRUMENT_FX_MAJORS_USD_CAD,
}

OFFER_SIDE = dukascopy_python.OFFER_SIDE_BID

_INTERVAL_LABELS = {
    dukascopy_python.INTERVAL_MIN_15: "M15",
    dukascopy_python.INTERVAL_HOUR_1: "H1",
}


def _cache_path(pair: str, interval, start: pd.Timestamp, end: pd.Timestamp) -> Path:
    label = _INTERVAL_LABELS.get(interval, str(interval))
    return CACHE_DIR / f"{pair}_{label}_{start.date()}_{end.date()}.parquet"


def fetch_pair_history(
    pair: str,
    start: str,
    end: str,
    interval=dukascopy_python.INTERVAL_MIN_15,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Real OHLCV bars for `pair` between `start` and `end` (both date strings).

    Cached to `data_cache/`; subsequent calls with the same (pair, interval,
    start, end) read the parquet file instead of re-hitting Dukascopy.
    """
    if pair not in _PAIR_TO_DUKASCOPY:
        raise ValueError(f"unknown pair {pair}, expected one of {PAIRS}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = _cache_path(pair, interval, start_ts, end_ts)

    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    df = dukascopy_python.fetch(
        _PAIR_TO_DUKASCOPY[pair],
        interval,
        OFFER_SIDE,
        start_ts.to_pydatetime(),
        end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index.name = "timestamp"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def load_all_pairs_real(
    start: str, end: str, interval=dukascopy_python.INTERVAL_MIN_15
) -> dict[str, pd.DataFrame]:
    return {pair: fetch_pair_history(pair, start, end, interval=interval) for pair in PAIRS}
