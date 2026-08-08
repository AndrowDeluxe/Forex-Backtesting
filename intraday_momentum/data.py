"""M5 Dukascopy data for the intraday-momentum research (Seeck 2026, SSRN
working paper -- see app_pages/fx_papers_202608.py Tab 3).

Separate cache/instrument map from `strategy/real_data.py` and
`combined_strategy/data.py` for two reasons: (1) this needs M5 bars, which
neither existing fetcher requests; (2) AUD/JPY and GBP/JPY are not in
either existing pair list. Own package, own cache dir, per this repo's
convention of not touching another strategy's pinned instrument map.
"""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka_instruments
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "intraday_momentum"

PAIRS = ["EURUSD", "GBPUSD", "AUDJPY", "GBPJPY", "USDJPY"]

_PAIR_TO_DUKASCOPY = {
    "EURUSD": duka_instruments.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka_instruments.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka_instruments.INSTRUMENT_FX_MAJORS_USD_JPY,
    "AUDJPY": duka_instruments.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "GBPJPY": duka_instruments.INSTRUMENT_FX_CROSSES_GBP_JPY,
}

OFFER_SIDE = dukascopy_python.OFFER_SIDE_BID
INTERVAL = dukascopy_python.INTERVAL_MIN_5


def _cache_path(pair: str, start: pd.Timestamp, end: pd.Timestamp) -> Path:
    return CACHE_DIR / f"{pair}_M5_{start.date()}_{end.date()}.parquet"


def fetch_pair_m5(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """M5 OHLCV bars for `pair`, cached to `data_cache/intraday_momentum/`."""
    if pair not in _PAIR_TO_DUKASCOPY:
        raise ValueError(f"unknown pair {pair!r}, expected one of {PAIRS}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = _cache_path(pair, start_ts, end_ts)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    df = dukascopy_python.fetch(
        _PAIR_TO_DUKASCOPY[pair],
        INTERVAL,
        OFFER_SIDE,
        start_ts.to_pydatetime(),
        end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index.name = "timestamp"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def load_all_pairs_m5(start: str, end: str) -> dict[str, pd.DataFrame]:
    return {pair: fetch_pair_m5(pair, start, end) for pair in PAIRS}
