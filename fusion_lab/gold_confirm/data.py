"""Freie Rohdaten fuer den Gold-Confirmation-Score. Jede Quelle -> eine Parquet-Datei in DATA_DIR.

Quellen (alle frei, kein Login):
  cftc.parquet    CFTC Disaggregated (Futures only), Gold + Silber ab 2006, alle Haendlergruppen + OI
  fred.parquet    GVZ, Realzins 10J, Breakeven 10J, EPU, 2J-Rendite, USDCNY (FRED, Key aus news_calendar)
  yf.parquet      GC=F, SI=F, HG=F, GLD, GDX, SLV, DXY: Close + Volume (yfinance)
  gld.parquet     GLD-Bestand in Tonnen je Tag (SPDR-Historienarchiv, xlsx)
  imf.parquet     Goldreserven aller Laender, Mio. Feinunzen, monatlich (IMF IRFCL)
  sge.parquet     Shanghai Gold Benchmark (CNY/g, AM `zp` + PM `wp`) ab 04/2016
  spot.parquet    XAUUSD D1 (Dukascopy-Cache, UTC-Tage)
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "fusion_lab" / "data" / "gold_confirm"
START = "2004-01-01"
UA = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 120

CFTC_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
CFTC_CODES = {"088691": "GOLD", "084691": "SILVER"}
CFTC_FIELDS = ["open_interest_all", "prod_merc_positions_long", "prod_merc_positions_short",
               "swap_positions_long_all", "swap__positions_short_all",
               "m_money_positions_long_all", "m_money_positions_short_all",
               "other_rept_positions_long", "other_rept_positions_short",
               "nonrept_positions_long_all", "nonrept_positions_short_all"]
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"gvz": "GVZCLS", "real10": "DFII10", "be10": "T10YIE", "epu": "USEPUINDXD",
               "us2y": "DGS2", "usdcny": "DEXCHUS"}
YF = {"gc": "GC=F", "si": "SI=F", "hg": "HG=F", "gld": "GLD", "gdx": "GDX", "slv": "SLV", "dxy": "DX-Y.NYB"}
GLD_URL = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"
IMF_URL = ("https://api.imf.org/external/sdmx/2.1/data/IMF.STA,IRFCL/"
           ".IRFCLDT1_IRFCL56V_FTO..M?startPeriod=2000-01")
SGE_URL = "https://www.sge.com.cn/graph/DayilyJzj"
SPOT_FILES = ["GOLD_D1_2009-01-01_2016-01-01.parquet", "GOLD_D1_2016-01-01_2026-11-01.parquet"]


def fetch_cftc() -> pd.DataFrame:
    codes = ",".join(f"'{c}'" for c in CFTC_CODES)
    r = requests.get(CFTC_URL, timeout=TIMEOUT, params={
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


def fetch_fred() -> pd.DataFrame:
    sys.path.insert(0, str(ROOT))
    from news_calendar._secrets import load_fred_api_key
    key, cols = load_fred_api_key(), {}
    for name, sid in FRED_SERIES.items():
        r = requests.get(FRED_URL, timeout=TIMEOUT, params={"series_id": sid, "api_key": key,
                                                            "file_type": "json", "observation_start": START})
        r.raise_for_status()
        obs = pd.DataFrame(r.json()["observations"])
        cols[name] = pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"]))
    return pd.DataFrame(cols)


def fetch_yf() -> pd.DataFrame:
    import yfinance as yf
    cols = {}
    for name, sym in YF.items():
        d = yf.download(sym, start=START, progress=False, auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        cols[f"{name}_close"] = d["Close"]
        cols[f"{name}_volume"] = d["Volume"]
    return pd.DataFrame(cols)


def fetch_gld() -> pd.DataFrame:
    r = requests.get(GLD_URL, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    x = pd.read_excel(io.BytesIO(r.content), sheet_name="US GLD Historical Archive")
    x = x[["Date", "Tonnes of Gold"]].rename(columns={"Date": "date", "Tonnes of Gold": "tonnes"})
    x["date"] = pd.to_datetime(x["date"], format="%d-%b-%Y", errors="coerce")
    x["tonnes"] = pd.to_numeric(x["tonnes"], errors="coerce")
    return x.dropna().set_index("date").sort_index()


def fetch_imf() -> pd.DataFrame:
    r = requests.get(IMF_URL, headers=UA, timeout=300)
    r.raise_for_status()
    rows = []
    for m in re.finditer(r'<Series ([^>]*)>(.*?)</Series>', r.text, re.S):
        country = re.search(r'COUNTRY="([^"]+)"', m.group(1)).group(1)
        # OBS_VALUE ist in Unzen (China 2024 = 72.190.000), SCALE ist nur Anzeige-Metadatum
        for y, mo, v in re.findall(r'TIME_PERIOD="(\d{4})-M(\d{2})" OBS_VALUE="([^"]+)"', m.group(2)):
            rows.append((country, pd.Timestamp(f"{y}-{mo}-01"), float(v) / 1e6))
    return pd.DataFrame(rows, columns=["country", "month", "moz"])  # Mio. Feinunzen


def fetch_sge() -> pd.DataFrame:
    r = requests.post(SGE_URL, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    am = {pd.to_datetime(t, unit="ms"): v for t, v in j["zp"]}
    pm = {pd.to_datetime(t, unit="ms"): v for t, v in j["wp"]}
    d = pd.DataFrame({"am": pd.Series(am), "pm": pd.Series(pm)})
    d.index = (d.index + pd.Timedelta(hours=8)).normalize()  # ms-Stempel = Mitternacht Peking in UTC
    return d.sort_index()


def load_spot() -> pd.DataFrame:
    parts = [pd.read_parquet(ROOT / "data_cache" / "combined" / f) for f in SPOT_FILES]
    d = pd.concat(parts)
    d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d[d.index.dayofweek < 5]


FETCHERS = {"cftc": fetch_cftc, "fred": fetch_fred, "yf": fetch_yf, "gld": fetch_gld, "imf": fetch_imf,
            "sge": fetch_sge, "spot": load_spot}


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / f"{name}.parquet")


def main(names: list[str] | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in names or FETCHERS:
        try:
            d = FETCHERS[name]()
            d.to_parquet(DATA_DIR / f"{name}.parquet")
            idx = d["report"] if "report" in d else d["month"] if "month" in d else d.index
            print(f"{name:5s} {len(d):6d} Zeilen  {pd.Series(idx).min():%Y-%m-%d} .. {pd.Series(idx).max():%Y-%m-%d}")
        except Exception as e:  # eine tote Quelle soll die anderen nicht blockieren
            print(f"{name:5s} FEHLER: {e}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
