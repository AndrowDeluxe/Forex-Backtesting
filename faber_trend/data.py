"""Eingefrorene Tagesdaten (OHLC) fuer den Faber-Trend-Funded-Test.

Regel (Nutzer 2026-10-04): einmal laden, als CSV mit Datum im Namen unter
scripts/frozen_data/ einfrieren, danach nur noch diese Dateien lesen.

SP500 nutzt die bereits eingefrorene ^SP500TR-Schlussreihe (Regressionstest
gegen research_faber_sp500tr.py); Open/High/Low werden aus ^GSPC relativ zum
GSPC-Schluss auf die TR-Reihe skaliert (^SP500TR selbst hat kaum H/L).
NASDAQ/US30 sind Preisindizes (keine Dividenden), DAX ist ein
Performance-Index. Futures (GC/SI/CL/ZN/ZB/HG) sind yfinance-Frontmonat,
also mit Roll-Spruengen -- Tagesspruenge > 10 % werden gemeldet.
"""
import glob
import os
from datetime import date

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN_DIR = os.path.join(ROOT, "scripts", "frozen_data")

# interner Name -> (yfinance-Ticker, Assetklasse)
INSTRUMENTS = {
    "SP500": ("^GSPC", "index"),
    "NASDAQ": ("^NDX", "index"),
    "US30": ("^DJI", "index"),
    "DAX": ("^GDAXI", "index"),
    "GOLD": ("GC=F", "commodity"),
    "SILVER": ("SI=F", "commodity"),
    "OIL": ("CL=F", "commodity"),
    "COPPER": ("HG=F", "commodity"),
    "TNOTE10": ("ZN=F", "bond"),
    "TBOND30": ("ZB=F", "bond"),
    "EURUSD": ("EURUSD=X", "fx"),
    "USDJPY": ("JPY=X", "fx"),
    # nur als Cross-Asset-Ziel (Variante D); Daten erst ab 2014 -> kein Lernfenster
    "BTC": ("BTC-USD", "crypto"),
}


def _frozen_path(name):
    files = sorted(glob.glob(os.path.join(FROZEN_DIR, f"{name.lower()}_ohlc_daily_*.csv")))
    return files[-1] if files else None


def _download(ticker, start="1985-01-01"):
    import yfinance as yf
    d = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close"]].dropna()
    d.columns = ["open", "high", "low", "close"]
    return d[d["close"] > 0]


def freeze_all():
    os.makedirs(FROZEN_DIR, exist_ok=True)
    tag = f"{date.today():%Y%m%d}"
    for name, (tick, _) in INSTRUMENTS.items():
        if _frozen_path(name):
            continue
        d = _download(tick)
        d.to_csv(os.path.join(FROZEN_DIR, f"{name.lower()}_ohlc_daily_{tag}.csv"), index_label="date")


def _sp500_tr():
    tr_file = sorted(glob.glob(os.path.join(FROZEN_DIR, "sp500tr_daily_*.csv")))[-1]
    tr = pd.read_csv(tr_file, index_col="date", parse_dates=True)["close"]
    px = pd.read_csv(_frozen_path("SP500"), index_col="date", parse_dates=True)
    px = px.reindex(tr.index)
    out = pd.DataFrame({"close": tr})
    for c in ("open", "high", "low"):
        out[c] = tr * (px[c] / px["close"])
    # fehlende GSPC-Tage: H/L/O = Schluss
    for c in ("open", "high", "low"):
        out[c] = out[c].fillna(out["close"])
    out["high"] = out[["high", "close", "open"]].max(axis=1)
    out["low"] = out[["low", "close", "open"]].min(axis=1)
    return out[["open", "high", "low", "close"]]


def load(name):
    if name == "SP500":
        df = _sp500_tr()
    else:
        df = pd.read_csv(_frozen_path(name), index_col="date", parse_dates=True)
        # unplausible Bars reparieren (Yahoo: High < Close o.ae.), nie loeschen
        df["high"] = df[["high", "close", "open"]].max(axis=1)
        df["low"] = df[["low", "close", "open"]].min(axis=1)
    return df.sort_index()


def spikes(df, thr=0.10):
    r = df["close"].pct_change()
    return r[r.abs() > thr]
