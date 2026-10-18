"""Dukascopy-M1 (Bid, UTC) fuer FX-Majors und US-Indizes, jahresweise gecacht.

Bid-Bars: der Spread steckt nicht in den Kursen, er wird in costs.py je
Rundturn voll abgezogen.
"""

import sys
from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka
import pandas as pd

CACHE = Path(__file__).resolve().parents[1] / "data_cache" / "smh_microstructure"

INSTRUMENTS = {
    "EURUSD": duka.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka.INSTRUMENT_FX_MAJORS_USD_JPY,
    "AUDUSD": duka.INSTRUMENT_FX_MAJORS_AUD_USD,
    # Frische Paare fuer die Key-Level-Edge-Card (16.10.2026)
    "USDCAD": duka.INSTRUMENT_FX_MAJORS_USD_CAD,
    "USDCHF": duka.INSTRUMENT_FX_MAJORS_USD_CHF,
    "NZDUSD": duka.INSTRUMENT_FX_MAJORS_NZD_USD,
    "EURJPY": duka.INSTRUMENT_FX_CROSSES_EUR_JPY,
    "GBPJPY": duka.INSTRUMENT_FX_CROSSES_GBP_JPY,
    "EURGBP": duka.INSTRUMENT_FX_CROSSES_EUR_GBP,
    "SP500": duka.INSTRUMENT_IDX_AMERICA_E_SANDP_500,
    "NASDAQ": duka.INSTRUMENT_IDX_AMERICA_E_NQ_100,
}
FIRST_YEAR = 2016
LAST_DAY = "2026-10-16"


def _year_path(sym: str, year: int) -> Path:
    # Laufendes Jahr traegt den Stichtag im Namen, damit es spaeter neu geladen wird
    suffix = "" if year < pd.Timestamp(LAST_DAY).year else f"_bis_{LAST_DAY}"
    return CACHE / f"{sym}_M1_{year}{suffix}.parquet"


def fetch_year(sym: str, year: int, force: bool = False) -> pd.DataFrame:
    path = _year_path(sym, year)
    last = pd.Timestamp(LAST_DAY)
    if path.exists() and not force:
        return pd.read_parquet(path)
    start = pd.Timestamp(f"{year}-01-01")
    end = min(pd.Timestamp(f"{year + 1}-01-01"), last)
    df = dukascopy_python.fetch(INSTRUMENTS[sym], dukascopy_python.INTERVAL_MIN_1,
                                dukascopy_python.OFFER_SIDE_BID,
                                start.to_pydatetime(), end.to_pydatetime())
    df = df.sort_index()
    df = df[~df.index.duplicated()]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index.name = "timestamp"
    out = df[["open", "high", "low", "close", "volume"]].astype("float64")
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out


def load(sym: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    last = pd.Timestamp(LAST_DAY)
    parts = [fetch_year(sym, y) for y in range(FIRST_YEAR, last.year + 1)]
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated()]
    if start:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df.index < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return df


def gap_report(sym: str) -> pd.DataFrame:
    """Je Jahr: Anzahl M1-Bars, Handelstage, Bars je Tag (Median), Tage mit < 50 % Abdeckung."""
    df = load(sym)
    day = df.index.floor("D")
    per_day = df.groupby(day).size()
    rep = per_day.groupby(per_day.index.year).agg(
        tage="size", bars_median="median",
        duenne_tage=lambda s: int((s < 0.5 * s.median()).sum()))
    rep["bars"] = df.groupby(df.index.year).size()
    return rep


if __name__ == "__main__":
    syms = sys.argv[1:] or list(INSTRUMENTS)
    for s in syms:
        for y in range(FIRST_YEAR, pd.Timestamp(LAST_DAY).year + 1):
            d = fetch_year(s, y)
            print(f"{s} {y}: {len(d):,} Bars  {d.index.min()} .. {d.index.max()}", flush=True)
