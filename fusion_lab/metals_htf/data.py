"""Rohdaten Edelmetalle HTF -> Parquet in fusion_lab/data/metals_htf/. Alles frei; FRED-Key aus news_calendar.

  yf.parquet    GC=F, SI=F, PL=F (OHLC), HG=F, DBC, DXY (Close)       Yahoo
  fred.parquet  DFII10, T10YIE, DGS2, DGS10, GVZCLS                   FRED
  cftc.parquet  Managed Money long/short + OI, Gold/Silber/Platin     CFTC Disaggregated (ab 2006)
  gld.parquet   GLD-Bestand in Tonnen                                 SPDR (Fetcher aus gold_confirm)
  imf.parquet   Goldreserven je Land, monatlich                       IMF IRFCL (Fetcher aus gold_confirm)

Aufruf: python -m fusion_lab.metals_htf.data [quelle ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

from fusion_lab.gold_confirm import data as gc_data

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "fusion_lab" / "data" / "metals_htf"
START = "2003-01-01"      # ein Jahr Vorlauf fuer 52-W-Merkmale vor IS-Start 2004
TIMEOUT = 120

YF_OHLC = {"gc": "GC=F", "si": "SI=F", "pl": "PL=F"}
YF_CLOSE = {"hg": "HG=F", "dbc": "DBC", "dxy": "DX-Y.NYB"}
FRED = {"real10": "DFII10", "be10": "T10YIE", "us2y": "DGS2", "us10y": "DGS10", "gvz": "GVZCLS"}
CFTC_CODES = {"088691": "GOLD", "084691": "SILVER", "076651": "PLATINUM"}
CFTC_FIELDS = ["open_interest_all", "m_money_positions_long_all", "m_money_positions_short_all"]


def _yf(sym: str) -> pd.DataFrame:
    import yfinance as yf
    d = yf.download(sym, start=START, progress=False, auto_adjust=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    return d


def fetch_yf() -> pd.DataFrame:
    cols = {}
    for k, sym in YF_OHLC.items():
        d = _yf(sym)
        for f in ("Open", "High", "Low", "Close"):
            cols[f"{k}_{f.lower()}"] = d[f]
    for k, sym in YF_CLOSE.items():
        cols[f"{k}_close"] = _yf(sym)["Close"]
    out = pd.DataFrame(cols).sort_index()
    return out[out.index.dayofweek < 5]


def fetch_fred() -> pd.DataFrame:
    sys.path.insert(0, str(ROOT))
    from news_calendar._secrets import load_fred_api_key
    key, cols = load_fred_api_key(), {}
    for k, sid in FRED.items():
        r = requests.get(gc_data.FRED_URL, timeout=TIMEOUT, params={"series_id": sid, "api_key": key,
                                                                    "file_type": "json", "observation_start": START})
        r.raise_for_status()
        obs = pd.DataFrame(r.json()["observations"])
        cols[k] = pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"]))
    return pd.DataFrame(cols)


def fetch_cftc() -> pd.DataFrame:
    codes = ",".join(f"'{c}'" for c in CFTC_CODES)
    r = requests.get(gc_data.CFTC_URL, timeout=TIMEOUT, params={
        "$where": f"cftc_contract_market_code in ({codes}) AND report_date_as_yyyy_mm_dd >= '2006-01-01T00:00:00.000'",
        "$select": ",".join(["cftc_contract_market_code", "report_date_as_yyyy_mm_dd", *CFTC_FIELDS]),
        "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": 50000})
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    out = pd.DataFrame({"market": d["cftc_contract_market_code"].map(CFTC_CODES),
                        "report": pd.to_datetime(d["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)})
    for c in CFTC_FIELDS:
        out[c] = pd.to_numeric(d[c], errors="coerce")
    return out


FETCHERS = {"yf": fetch_yf, "fred": fetch_fred, "cftc": fetch_cftc, "gld": gc_data.fetch_gld, "imf": gc_data.fetch_imf}


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / f"{name}.parquet")


def main(names: list[str] | None = None) -> dict[str, str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    status = {}
    for n in names or FETCHERS:
        try:
            d = FETCHERS[n]()
            d.to_parquet(DATA_DIR / f"{n}.parquet")
            idx = d["report"] if "report" in d else d["month"] if "month" in d else d.index
            status[n] = f"{len(d)} Zeilen {pd.Series(idx).min():%Y-%m-%d} .. {pd.Series(idx).max():%Y-%m-%d}"
        except Exception as e:  # eine tote Quelle soll die anderen nicht blockieren
            status[n] = f"FEHLER: {e}"
        print(f"{n:5s} {status[n]}")
    return status


if __name__ == "__main__":
    main(sys.argv[1:] or None)
