"""Zins-Langhistorie ab 2003 fuer die Remy-King-Tests A1 (Fair Value) und A2 (Carry).

    python -m scripts.remy_rates_history

Die Datenschicht `fusion_lab/macro_data` haelt nur ab 2015; die Tests brauchen den
Carry-Crash 2008 im IS. Nutzt die Parser der Datenschicht, schreibt aber nur in den
Forschungs-Cache `data_cache/remy/rates_history.parquet` (key, date, value).

Quellen: BIS WS_CBPOL (Leitzinsen, taeglich), FRED DGS2/VIXCLS, EZB-AAA-Kurve 2J,
MoF Japan (JGB 2J), BoC Valet (2J), BoE GLC-Nominalkurve (2J Spot).
JP-Leitzins vor 09.03.2006 fehlt bei der BIS (Mengensteuerung) -> 0,0 eingesetzt.
"""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from fusion_lab.macro_data import sources

START = "2002-06-01"
OUT = Path("data_cache/remy/rates_history.parquet")
BOE_GLC = "https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/glcnominalddata.zip"
BOE_FILES = ["GLC Nominal daily data_2000 to 2004.xlsx", "GLC Nominal daily data_2005 to 2015.xlsx",
             "GLC Nominal daily data_2016 to 2024.xlsx", "GLC Nominal daily data_2025 to present.xlsx"]
HEADERS = {"User-Agent": "Mozilla/5.0 research-script"}


def policy_rates() -> pd.DataFrame:
    areas = "+".join(sources.BIS_AREA)
    r = requests.get(f"{sources.BIS_API}/WS_CBPOL/D.{areas}/all",
                     params={"startPeriod": START, "format": "csv"}, timeout=180)
    r.raise_for_status()
    df = sources.parse_bis(r.text, "policy_rate").dropna()
    jp_start = df.loc[df["key"] == "JP.policy_rate", "date"].min()
    fill = pd.bdate_range(START, jp_start - pd.Timedelta(days=1))
    jp0 = pd.DataFrame({"key": "JP.policy_rate", "date": fill, "value": 0.0})
    return pd.concat([df, jp0], ignore_index=True)


def fred(keys: dict[str, str]) -> pd.DataFrame:
    api_key = sources._fred_key()
    out = []
    for key, series in keys.items():
        r = requests.get(sources.FRED_API, params={"series_id": series, "api_key": api_key, "file_type": "json",
                                                   "observation_start": START}, timeout=90)
        r.raise_for_status()
        obs = pd.DataFrame(r.json()["observations"])
        s = pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"]))
        out.append(sources._long(key, s.dropna()))
    return pd.concat(out, ignore_index=True)


def _get(url: str, **kw) -> requests.Response:
    """EZB/BoE antworten bei grossen Abrufen gelegentlich mit 504 -> bis zu drei Versuche."""
    for attempt in range(3):
        r = requests.get(url, **kw)
        if r.status_code < 500 or attempt == 2:
            r.raise_for_status()
            return r
        time.sleep(20)


def ecb_2y() -> pd.DataFrame:
    """AAA-Kurve beginnt im September 2004."""
    r = _get(f"{sources.ECB_API}/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
             params={"startPeriod": "2004-09-01", "format": "csvdata"}, timeout=300)
    df = pd.read_csv(io.StringIO(r.text))
    s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values, index=pd.to_datetime(df["TIME_PERIOD"]))
    return sources._long("EA.2y", s.dropna())


def mof_2y() -> pd.DataFrame:
    parts = []
    for name in ("historical/jgbcme_all.csv", "jgbcme.csv"):
        r = requests.get(f"{sources.MOF_URL}/{name}", timeout=180)
        r.raise_for_status()
        parts.append(sources.parse_mof(r.content.decode("latin-1")))
    df = pd.concat(parts, ignore_index=True).drop_duplicates(["key", "date"], keep="last")
    return df[(df["key"] == "JP.2y") & (df["date"] >= START)]


def boc_2y() -> pd.DataFrame:
    r = requests.get(f"https://www.bankofcanada.ca/valet/observations/{','.join(sources.BOC_YIELDS.values())}/csv",
                     params={"start_date": START}, timeout=180)
    r.raise_for_status()
    df = sources.parse_boc(r.text)
    return df[df["key"] == "CA.2y"]


def parse_boe_glc(xlsx: bytes) -> pd.Series:
    """Blatt '4. spot curve': Kopf mit Laufzeiten in Jahren (Zeile 'years:'), Daten ab dem ersten Datum."""
    book = pd.ExcelFile(io.BytesIO(xlsx))
    sheet = [s for s in book.sheet_names if "spot curve" in s.lower() and "short" not in s.lower()][0]
    raw = book.parse(sheet, header=None)
    head = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower().str.startswith("years")][0]
    col = [c for c in raw.columns if pd.to_numeric(raw.iloc[head, c], errors="coerce") == 2.0][0]
    body = raw.iloc[head + 1:]
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce")
    s = pd.Series(pd.to_numeric(body[col], errors="coerce").values, index=dates)
    return s[s.index.notna()].dropna()


def boe_2y() -> pd.DataFrame:
    r = _get(BOE_GLC, timeout=300, headers=HEADERS)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    s = pd.concat([parse_boe_glc(z.read(f)) for f in BOE_FILES]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return sources._long("GB.2y", s[s.index >= START])


def main() -> None:
    jobs = {"policy": policy_rates, "fred": lambda: fred({"US.2y": "DGS2", "MKT.vix": "VIXCLS"}),
            "ecb": ecb_2y, "mof": mof_2y, "boc": boc_2y, "boe": boe_2y}
    parts = []
    for name, job in jobs.items():  # je Quelle zwischenspeichern: ein Ausfall wiederholt nicht alle Abrufe
        cache = OUT.parent / f"_part_{name}.parquet"
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            job().to_parquet(cache, index=False)
        parts.append(pd.read_parquet(cache))
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(df.groupby("key")["date"].agg(["min", "max", "size"]).to_string())


if __name__ == "__main__":
    main()
