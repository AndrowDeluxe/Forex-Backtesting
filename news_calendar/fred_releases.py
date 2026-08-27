"""US High-Impact-Release-Termine via FRED-API (fred/release/dates). Vier
Releases per DOM-Suche in der FRED-API bestaetigt (2026-08-12, siehe
fred/releases-Endpoint -- kein ISM/PMI dort verfuegbar):
    9  Advance Monthly Sales for Retail and Food Services (Retail Sales)
    10 Consumer Price Index (CPI)
    50 Employment Situation (NFP)
    53 Gross Domestic Product (GDP)

Cached als CSV unter data_cache/news_calendar/ (gitignored), damit nicht bei
jedem Backtest-Lauf neu gegen die API gefragt wird."""

from pathlib import Path

import pandas as pd
import requests

from ._secrets import load_fred_api_key

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "news_calendar"
FRED_BASE = "https://api.stlouisfed.org/fred/release/dates"

RELEASES = {
    "us_retail_sales": 9,
    "us_cpi": 10,
    "us_nfp": 50,
    "us_gdp": 53,
}


def fetch_release_dates(release_key: str, start: str, end: str, force_refresh: bool = False) -> pd.DatetimeIndex:
    if release_key not in RELEASES:
        raise ValueError(f"unknown release_key {release_key!r}, expected one of {list(RELEASES)}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"fred_{release_key}_{start}_{end}.csv"
    if cache_path.exists() and not force_refresh:
        return pd.DatetimeIndex(pd.read_csv(cache_path)["date"])

    key = load_fred_api_key()
    r = requests.get(FRED_BASE, params={
        "release_id": RELEASES[release_key], "api_key": key, "file_type": "json",
        "realtime_start": start, "realtime_end": end,
        "include_release_dates_with_no_data": "true",
    }, timeout=30)
    r.raise_for_status()
    dates = pd.DatetimeIndex(sorted(d["date"] for d in r.json()["release_dates"]))
    pd.Series(dates, name="date").to_frame().to_csv(cache_path, index=False)
    return dates


def fetch_all_us_release_dates(start: str, end: str, force_refresh: bool = False) -> pd.DatetimeIndex:
    """Vereinigung aller vier US-Releases -- fuer den 'ganz simplen' Filter,
    der nicht zwischen den Release-Typen unterscheidet."""
    all_dates: set[pd.Timestamp] = set()
    for key in RELEASES:
        all_dates.update(fetch_release_dates(key, start, end, force_refresh=force_refresh))
    return pd.DatetimeIndex(sorted(all_dates))
