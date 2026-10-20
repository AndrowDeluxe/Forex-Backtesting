"""Daten fuer die Regimekarte.

Makro (wie im Original): Erstveroeffentlichungen aus ALFRED, ueber die FRED-API
mit allen Vintages (realtime 1776..9999).
  - Wachstum:  GDPC1 (reales BIP, Quartal), YoY je Vintage. ALFRED-Vintages
               ab 04.12.1991, reicht fuer den Start Maerz 1994.
  - Inflation: CPIAUCNS (Headline-CPI, nicht saisonbereinigt; YoY ist
               ohnehin saisonneutral und NSA wird praktisch nie revidiert).

Assets: Das Original nutzt Bloomberg. Hier freie Ersatzreihen, Abweichungen
bewusst und dokumentiert:
  SPX    ^SP500TR (yfinance)          = gleich (S&P 500 Total Return)
  UST    synthetische 5y-Par-Anleihe aus FRED DGS5 (Carry + Duration x dy);
         Bloomberg-Treasury-Index hat ~5-6 J. Duration; 7y gab 5,6 % Vola statt 4,3 %
  Gold   GC=F, Copper HG=F, Crude CL=F, Wheat ZW=F (yfinance, Front-Monat,
         ungerollt -> preisnah, ohne Rollrendite; erst ab Aug. 2000)
  DXY    DX-Y.NYB (yfinance)          = gleich
  Cash   FRED DTB3 (3M T-Bill, Diskontsatz p.a.), Tagesertrag = Satz/252
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data_cache" / "macro_regime"
FRED_API = "https://api.stlouisfed.org/fred"

MACRO_SERIES = {"growth": "GDPC1", "inflation": "CPIAUCNS"}
FRED_RELEASES = {"growth": 53, "inflation": 10}  # GDP, CPI (wie news_calendar)

YF_ASSETS = {"SPX": "^SP500TR", "Gold": "GC=F", "Copper": "HG=F",
             "Crude": "CL=F", "Wheat": "ZW=F", "DXY": "DX-Y.NYB"}
ASSETS = ["SPX", "UST", "Gold", "Copper", "Crude", "Wheat", "DXY"]
UST_MATURITY = 5.0


def _fred_key() -> str:
    sys.path.insert(0, str(ROOT))
    from news_calendar._secrets import load_fred_api_key
    return load_fred_api_key()


def _cached(name: str, refresh: bool, build) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    df = build()
    df.to_parquet(path)
    return df


def fetch_vintages(series: str, refresh: bool = False) -> pd.DataFrame:
    """Alle Vintages: Spalten date (Periode), value, realtime_start, realtime_end."""
    def build():
        r = requests.get(f"{FRED_API}/series/observations", params={
            "series_id": series, "api_key": _fred_key(), "file_type": "json",
            "realtime_start": "1776-07-04", "realtime_end": "9999-12-31",
            "observation_start": "1985-01-01"}, timeout=120)
        r.raise_for_status()
        df = pd.DataFrame(r.json()["observations"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df["realtime_start"] = pd.to_datetime(df["realtime_start"])
        df["realtime_end"] = pd.to_datetime(df["realtime_end"].replace("9999-12-31", "2262-04-11"))
        return df.dropna(subset=["value"])[["date", "value", "realtime_start", "realtime_end"]]
    return _cached(f"vintages_{series}", refresh, build)


def fetch_release_dates(kind: str, start: str = "2026-01-01", end: str = "2027-12-31",
                        refresh: bool = False) -> pd.DatetimeIndex:
    """Release-Termine inkl. kuenftiger (FRED-Kalender), fuer "naechste Prints"."""
    def build():
        r = requests.get(f"{FRED_API}/release/dates", params={
            "release_id": FRED_RELEASES[kind], "api_key": _fred_key(), "file_type": "json",
            "realtime_start": start, "realtime_end": end, "sort_order": "asc",
            "include_release_dates_with_no_data": "true"}, timeout=60)
        r.raise_for_status()
        return pd.DataFrame({"date": pd.to_datetime([d["date"] for d in r.json()["release_dates"]])})
    return pd.DatetimeIndex(_cached(f"release_dates_{kind}", refresh, build)["date"])


def fetch_fred_daily(series: str, refresh: bool = False) -> pd.Series:
    def build():
        r = requests.get(f"{FRED_API}/series/observations", params={
            "series_id": series, "api_key": _fred_key(), "file_type": "json"}, timeout=60)
        r.raise_for_status()
        df = pd.DataFrame(r.json()["observations"])
        return pd.DataFrame({series: pd.to_numeric(df["value"], errors="coerce").values},
                            index=pd.to_datetime(df["date"])).dropna()
    return _cached(f"fred_{series}", refresh, build)[series]


def fetch_yf(refresh: bool = False) -> pd.DataFrame:
    def build():
        import yfinance as yf
        cols = {}
        for name, ticker in YF_ASSETS.items():
            d = yf.download(ticker, start="1990-01-01", progress=False, auto_adjust=True)
            cols[name] = d["Close"].squeeze()
        df = pd.DataFrame(cols)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df
    return _cached("yf_prices", refresh, build)


def synthetic_par_bond_returns(yld_pct: pd.Series, maturity: float = UST_MATURITY) -> pd.Series:
    """Tagesrendite einer Par-Anleihe mit konstanter Laufzeit: Carry + Preiseffekt
    (Modified Duration und Konvexitaet bei Par, halbjaehrlicher Kupon)."""
    y = yld_pct / 100.0
    y_prev = y.shift(1)
    dy = y - y_prev
    h = y_prev / 2
    n = 2 * maturity
    mod_dur = (1 - (1 + h) ** -n) / y_prev.where(y_prev > 1e-6)
    mod_dur = mod_dur.fillna(maturity)
    convexity = mod_dur ** 2  # grobe Naeherung, Effekt minimal
    days = y.index.to_series().diff().dt.days.fillna(1)
    return y_prev * days / 365 - mod_dur * dy + 0.5 * convexity * dy ** 2


def asset_excess_returns(refresh: bool = False) -> pd.DataFrame:
    """Tagesrendite je Asset minus Cash-Tagesertrag, auf SPX-Handelstagen."""
    px = fetch_yf(refresh)
    rets = {}
    for name in YF_ASSETS:
        p = px[name].dropna()
        p_prev = p.shift(1)
        r = p / p_prev - 1
        rets[name] = r.where((p > 0) & (p_prev > 0))  # CL=F am 20.04.2020 negativ
    rets["UST"] = synthetic_par_bond_returns(fetch_fred_daily("DGS5", refresh).dropna())
    rets = pd.DataFrame(rets)
    spx_days = px["SPX"].dropna().index
    rets = rets.reindex(spx_days)
    cash = fetch_fred_daily("DTB3", refresh).reindex(spx_days).ffill() / 100 / 252
    return rets[ASSETS].sub(cash, axis=0).iloc[1:]
