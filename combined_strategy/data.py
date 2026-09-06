"""Multi-timeframe Dukascopy data for the combined strategy: the 6 FX majors
from the ADX-VWAP paper plus Gold, Silver, S&P 500, Nasdaq-100, and Oil.

H4 is the EMA S/R trigger timeframe; Daily/Weekly feed the EMA bias. Unlike
the original EMA S/R project (yfinance, hourly capped at 730 days), Dukascopy
gives the full ~10-year history at every timeframe, with real traded volume
(needed for the VWAP-overextension filter) - a genuine upgrade, not just a
re-plumbing exercise.
"""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "combined"

INSTRUMENTS = {
    "EURUSD": duka.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka.INSTRUMENT_FX_MAJORS_USD_JPY,
    "USDCHF": duka.INSTRUMENT_FX_MAJORS_USD_CHF,
    "AUDUSD": duka.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCAD": duka.INSTRUMENT_FX_MAJORS_USD_CAD,
    "GOLD": duka.INSTRUMENT_FX_METALS_XAU_USD,
    "SILVER": duka.INSTRUMENT_FX_METALS_XAG_USD,
    "PLATINUM": duka.INSTRUMENT_CMD_METALS_XPT_CMD_USD,
    "CHFJPY": duka.INSTRUMENT_FX_CROSSES_CHF_JPY,
    "SP500": duka.INSTRUMENT_IDX_AMERICA_E_SANDP_500,
    "NASDAQ": duka.INSTRUMENT_IDX_AMERICA_E_NQ_100,
    "US30": duka.INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    "VIX": duka.INSTRUMENT_IDX_AMERICA_VOL_IDX_USD,
    "OIL": duka.INSTRUMENT_CMD_ENERGY_E_LIGHT,
    # --- Zusaetzliche Kreuze fuer die paar-spezifische Waehrungsstaerke
    # (cls_practical/currency_strength.py, 2026-08-18) -- EUR/JPY selbst als
    # Handelspaar, der Rest als Referenzkreuze fuer die EUR-/JPY-/CAD-/AUD-
    # Staerke-Baskets (EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD,
    # CHF/JPY sind oben bereits vorhanden).
    "EURJPY": duka.INSTRUMENT_FX_CROSSES_EUR_JPY,
    "EURGBP": duka.INSTRUMENT_FX_CROSSES_EUR_GBP,
    "EURCHF": duka.INSTRUMENT_FX_CROSSES_EUR_CHF,
    "EURCAD": duka.INSTRUMENT_FX_CROSSES_EUR_CAD,
    "EURAUD": duka.INSTRUMENT_FX_CROSSES_EUR_AUD,
    "GBPJPY": duka.INSTRUMENT_FX_CROSSES_GBP_JPY,
    "GBPCAD": duka.INSTRUMENT_FX_CROSSES_GBP_CAD,
    "GBPAUD": duka.INSTRUMENT_FX_CROSSES_GBP_AUD,
    "CADJPY": duka.INSTRUMENT_FX_CROSSES_CAD_JPY,
    "CADCHF": duka.INSTRUMENT_FX_CROSSES_CAD_CHF,
    "AUDJPY": duka.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "AUDCAD": duka.INSTRUMENT_FX_CROSSES_AUD_CAD,
    "AUDCHF": duka.INSTRUMENT_FX_CROSSES_AUD_CHF,
}

OFFER_SIDE = dukascopy_python.OFFER_SIDE_BID
_TF_INTERVAL = {
    "M1": dukascopy_python.INTERVAL_MIN_1,
    "M5": dukascopy_python.INTERVAL_MIN_5,
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "M30": dukascopy_python.INTERVAL_MIN_30,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
    "H4": dukascopy_python.INTERVAL_HOUR_4,
    "D1": dukascopy_python.INTERVAL_DAY_1,
    "W1": dukascopy_python.INTERVAL_WEEK_1,
}


def _cache_path(key: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp) -> Path:
    return CACHE_DIR / f"{key}_{timeframe}_{start.date()}_{end.date()}.parquet"


def validate_ohlc_numeric(df: pd.DataFrame, columns: list[str]) -> None:
    """Guards against caching a corrupted Dukascopy response (Fund 2026-09-02,
    recurred 2026-09-03 across CTNL-Edge-/Trend-Pullback-/CLS-Practical-Scan
    simultaneously): a bad fetch occasionally comes back with one of these
    columns as strings instead of floats, which then blows up much later
    with "'>' not supported between instances of 'str' and 'float'" deep in
    a strategy's indicator code, and (worse) gets cached, so the bad data
    keeps getting served. Raise here instead so the caller's existing
    _retry() wrapper re-fetches rather than ever caching it.

    Fund 2026-09-06: a fetch window with ZERO matching bars (e.g. a request
    that falls entirely on a weekend/market holiday) comes back as a valid,
    legitimately empty DataFrame -- but pandas then has no values to infer a
    dtype from, so every column shows up as `object`, which used to trip
    this same "corrupted data" check as a false positive. That wasted 6
    retries (~8 minutes) and then crashed instead of just returning the
    correctly-empty result. An empty frame is never corrupted, only a
    non-empty one with the wrong dtype is -- skip the check for len(df)==0."""
    if df.empty:
        return
    for col in columns:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"fetched data has non-numeric column {col!r} (dtype {df[col].dtype}) - refusing to cache")


def fetch_timeframe(key: str, timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if key not in INSTRUMENTS:
        raise ValueError(f"unknown instrument key {key!r}, expected one of {list(INSTRUMENTS)}")
    if timeframe not in _TF_INTERVAL:
        raise ValueError(f"unknown timeframe {timeframe!r}, expected one of {list(_TF_INTERVAL)}")

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    path = _cache_path(key, timeframe, start_ts, end_ts)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    df = dukascopy_python.fetch(
        INSTRUMENTS[key], _TF_INTERVAL[timeframe], OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index.name = "timestamp"
    # Match ema_strategy's OHLC column naming (capitalised) so the existing
    # EMA/ADX indicator code can be reused unmodified.
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    # Fund 2026-09-02, siehe validate_ohlc_numeric()-Docstring oben (Fehlversuch
    # wird nie gecacht) -- frueher stand hier zusaetzlich eine inline duplizierte
    # Kopie derselben Pruefung (Fund 2026-09-06: die Duplizierung liess den
    # Wochenend-Leerfetch-Fix oben unwirksam wirken, weil diese zweite Kopie ihn
    # nicht mitbekam und weiterhin auch auf leeren DataFrames warf). Entfernt --
    # eine einzige Pruefstelle statt zwei synchron zu haltender Kopien.
    validate_ohlc_numeric(df, ["Open", "High", "Low", "Close", "Volume"])

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_multi_timeframe(key: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (h4, daily, weekly) OHLCV DataFrames for `key`."""
    h4 = fetch_timeframe(key, "H4", start, end)
    daily = fetch_timeframe(key, "D1", start, end)
    weekly = fetch_timeframe(key, "W1", start, end)
    return h4, daily, weekly


def load_all(start: str, end: str, keys=tuple(INSTRUMENTS)) -> dict[str, tuple]:
    return {key: fetch_multi_timeframe(key, start, end) for key in keys}
