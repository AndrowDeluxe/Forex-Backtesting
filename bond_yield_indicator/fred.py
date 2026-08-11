"""10-year government bond yields via FRED's public CSV endpoint (no API key
needed: https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>).

Resolution caveat (see knowledge/projects/bond-yield-spread-indikator.md,
"Hybrid" decision): only the US series is daily. The other 6 countries'
FRED series are the OECD "long-term government bond yield" mirror, MONTHLY
(median gap ~31 days), not daily like the source paper's own data (Bundesbank/
BoE/MOF/BoC/SNB/RBA). Verified empirically 2026-08-10 - checked here, not
assumed:
    US DGS10            daily,   1962-01-02 ..
    DE IRLTLT01DEM156N   monthly, 1956-05-01 ..
    UK IRLTLT01GBM156N   monthly, 1960-01-01 ..
    JP IRLTLT01JPM156N   monthly, 1989-01-01 ..
    CA IRLTLT01CAM156N   monthly, 1955-01-01 ..
    CH IRLTLT01CHM156N   monthly, 1955-01-01 ..
    AU IRLTLT01AUM156N   monthly, 1969-07-01 ..

This is a deliberate scope decision (fast V1), not an oversight: Layer 1
(spread.py) forward-fills the monthly series onto a daily grid and discloses
the resulting resolution loss per country. To upgrade a single country to a
true daily source later (Bundesbank API, BoE IADB, MOF Japan CSV, BoC Valet
API, SNB Data Portal, RBA F2 tables), only FREQUENCY[<country>] and a new
fetch function need to change here - spread.py/beta.py/indicator.py consume
fetch_yield()'s output unchanged regardless of source frequency."""

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "bond_yield_indicator"

# country -> (FRED series id, FX pair, is_usd_base)
# is_usd_base=True means the pair is USDxxx (USD is the base currency), so a
# RISING foreign yield relative to the US, all else equal, pulls the pair the
# OPPOSITE direction of a EURUSD-style (xxxUSD) pair - handled in indicator.py.
COUNTRIES = {
    "US": {"series": "DGS10", "pair": None, "usd_base": None},
    "DE": {"series": "IRLTLT01DEM156N", "pair": "EURUSD", "usd_base": False},
    "UK": {"series": "IRLTLT01GBM156N", "pair": "GBPUSD", "usd_base": False},
    "JP": {"series": "IRLTLT01JPM156N", "pair": "USDJPY", "usd_base": True},
    "CA": {"series": "IRLTLT01CAM156N", "pair": "USDCAD", "usd_base": True},
    "CH": {"series": "IRLTLT01CHM156N", "pair": "USDCHF", "usd_base": True},
    "AU": {"series": "IRLTLT01AUM156N", "pair": "AUDUSD", "usd_base": False},
}

FREQUENCY = {"US": "daily", "DE": "monthly", "UK": "monthly", "JP": "monthly",
             "CA": "monthly", "CH": "monthly", "AU": "monthly"}

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


def fetch_yield(country: str, force_refresh: bool = False) -> pd.Series:
    """Full-history 10y yield series for `country` (percent), FRED series id
    from COUNTRIES. Cached to parquet; FRED itself has no start/end params on
    this endpoint (always returns full history), so there is one cache file
    per series, refreshed wholesale rather than by date range."""
    if country not in COUNTRIES:
        raise ValueError(f"unknown country {country!r}, expected one of {list(COUNTRIES)}")
    series_id = COUNTRIES[country]["series"]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"yield_{country}_{series_id}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)["value"]

    url = FRED_CSV_URL.format(series=series_id)
    df = pd.read_csv(url)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["value"]).set_index("date").sort_index()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])

    df.to_parquet(path)
    return df["value"]


def fetch_all_yields(force_refresh: bool = False) -> dict[str, pd.Series]:
    return {c: fetch_yield(c, force_refresh=force_refresh) for c in COUNTRIES}
