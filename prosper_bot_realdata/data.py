"""Kursdaten fuer den Prosper-Bot-Echtdatentest (Lock `prosper_bot_realdata`).

Setzt je Markt/Zeitrahmen die Teildateien aus data_cache/combined bzw.
data_cache_crypto zusammen. Zusammensetzen NICHT per Vereinigung aller Zeitstempel
(verschiedene Abrufe koennen um 1 h verschobene Stempel haben -> doppelte Bars,
siehe Memory "Lake-Zeitstempel-Verschiebung"), sondern: laengste Datei als Basis,
andere Dateien nur VOR deren Anfang bzw. NACH deren Ende anhaengen.

Indizes (Dukascopy) enthalten Stummel-Bars ausserhalb der Handelszeit
(High == Low, Volume ~1) -- die werden verworfen.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COMBINED = ROOT / "data_cache" / "combined"
CRYPTO = ROOT / "data_cache_crypto"

FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
INDICES = ["SP500", "NASDAQ", "US30"]
METALS = ["GOLD"]
CRYPTOS = ["BTC", "ETH"]
MARKETS = INDICES + CRYPTOS + METALS + FX
TIMEFRAMES = ["M15", "H1", "D1"]

_CRYPTO_TF = {"M15": "15m", "H1": "1h", "D1": "1d", "M5": "5m"}
_RULE = {"M15": "15min", "H1": "1h"}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def kind(market: str) -> str:
    if market in CRYPTOS:
        return "crypto"
    if market in INDICES:
        return "index"
    if market in METALS:
        return "metal"
    return "fx"


def _files(market: str, tf: str) -> list[Path]:
    if kind(market) == "crypto":
        return sorted(CRYPTO.glob(f"{market}USDT_{_CRYPTO_TF[tf]}_*.parquet"))
    return sorted(COMBINED.glob(f"{market}_{tf}_*.parquet"))


def _read(path: Path) -> pd.DataFrame:
    d = pd.read_parquet(path)
    d = d.rename(columns={c: c.capitalize() for c in d.columns})
    d = d[["Open", "High", "Low", "Close"]].astype(float)
    idx = pd.DatetimeIndex(d.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    d.index = idx.as_unit("ns")
    return d[~d.index.duplicated(keep="last")].sort_index()


def _stitch(paths: list[Path]) -> pd.DataFrame:
    frames = [f for f in (_read(p) for p in paths) if len(f)]
    if not frames:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
    frames.sort(key=lambda f: f.index[-1] - f.index[0], reverse=True)
    base = frames[0]
    lo, hi = base.index[0], base.index[-1]
    parts = [base]
    for f in frames[1:]:
        before = f[f.index < lo]
        after = f[f.index > hi]
        if len(before):
            parts.append(before)
            lo = before.index[0]
        if len(after):
            parts.append(after)
            hi = after.index[-1]
    out = pd.concat(parts).sort_index()
    return out[~out.index.duplicated(keep="first")]


def _clean(d: pd.DataFrame, market: str) -> pd.DataFrame:
    d = d.dropna()
    d = d[(d[["Open", "High", "Low", "Close"]] > 0).all(axis=1)]
    if kind(market) == "index":
        d = d[d["High"] > d["Low"]]  # Stummel-Bars ausserhalb der Handelszeit
    return d


def _resample(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    g = d.resample(rule, label="left", closed="left")
    out = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(),
                        "Low": g["Low"].min(), "Close": g["Close"].last()})
    return out.dropna()


def _fold_weekend(d: pd.DataFrame) -> pd.DataFrame:
    """Muster htf_daily_trade/ipda_cycles.py::load_daily: So -> Mo, Sa -> Fr."""
    idx = d.index.tz_convert(None)
    key = idx.normalize()
    dow = idx.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1))
    key = key.where(dow != 5, key - pd.Timedelta(days=1))
    g = d.groupby(key)
    out = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(),
                        "Low": g["Low"].min(), "Close": g["Close"].last()})
    out = out[out.index.dayofweek < 5]
    out.index = out.index.tz_localize("UTC")
    return out


def load(market: str, tf: str) -> pd.DataFrame:
    """OHLC in UTC. Leeres Frame, wenn keine Daten vorhanden."""
    d = _clean(_stitch(_files(market, tf)), market)
    if tf in ("M15", "H1"):
        # kuerzere Quelle? aus feinerem Zeitrahmen zusammenfassen
        finer = {"H1": ["M15", "M5"], "M15": ["M5"]}[tf]
        for f_tf in finer:
            if len(d) and d.index[0] <= pd.Timestamp("2017-10-01", tz="UTC"):
                break
            src = _clean(_stitch(_files(market, f_tf)), market)
            if len(src) and (not len(d) or src.index[0] < d.index[0]):
                alt = _resample(src, _RULE[tf])
                d = _stitch_frames(alt, d)
    if tf == "D1":
        if kind(market) != "crypto":
            d = _fold_weekend(d)
    return d


def _stitch_frames(base: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    """base (aus feinerem TF) bevorzugt; extra nur ausserhalb von base anhaengen."""
    if not len(extra):
        return base
    if not len(base):
        return extra
    parts = [base, extra[extra.index < base.index[0]], extra[extra.index > base.index[-1]]]
    out = pd.concat(parts).sort_index()
    return out[~out.index.duplicated(keep="first")]


def coverage(d: pd.DataFrame) -> pd.Series:
    """Bars je Kalenderjahr."""
    if not len(d):
        return pd.Series(dtype=int)
    return d.groupby(d.index.year).size()


if __name__ == "__main__":
    rows = []
    for tf in TIMEFRAMES:
        for m in MARKETS:
            d = load(m, tf)
            cov = coverage(d)
            rows.append({"tf": tf, "market": m, "bars": len(d),
                         "start": d.index[0].date() if len(d) else None,
                         "end": d.index[-1].date() if len(d) else None,
                         **{str(y): int(cov.get(y, 0)) for y in range(2017, 2027)}})
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))
