"""Gemeinsame Daten fuer die Remy-King-Tests A1/A2: Tagesschluesse der 7 USD-Paare und
Zinsen aus `data_cache/remy/rates_history.parquet` (siehe scripts/remy_rates_history.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
FX_FILES = ["{}_D1_2003-01-01_2026-10-10.parquet", "{}_D1_2026-09-11_2026-11-10.parquet"]
CCY = {"EURUSD": "EA", "GBPUSD": "GB", "AUDUSD": "AU", "NZDUSD": "NZ", "USDCAD": "CA", "USDCHF": "CH", "USDJPY": "JP"}
CURRENCIES = ["US", "EA", "GB", "JP", "CH", "AU", "CA", "NZ"]
# Halber Round-Trip-Spread je Umschichtung als Anteil des Kurses (htf_daily_trade/backtest_r.MARKETS,
# fuer NZD/CAD/CHF wie AUD angesetzt).
HALF_SPREAD = {"EURUSD": 0.5e-4 / 1.10, "GBPUSD": 0.7e-4 / 1.30, "AUDUSD": 0.65e-4 / 0.70,
               "NZDUSD": 0.8e-4 / 0.65, "USDCAD": 0.8e-4 / 1.30, "USDCHF": 0.8e-4 / 0.90, "USDJPY": 0.006 / 120}
SWAP_MARKUP = 0.01  # Broker-Aufschlag p.a. je Positionsseite (Annahme, echte historische Swaps fehlen)
RATES = "data_cache/remy/rates_history.parquet"


def _daily_close(path: str) -> pd.Series:
    d = pd.read_parquet(path)["Close"].sort_index()
    idx = d.index.tz_convert(None) if d.index.tz is not None else d.index
    key = idx.normalize()
    dow = idx.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1))   # So -> Mo
    key = key.where(dow != 5, key - pd.Timedelta(days=1))   # Sa -> Fr
    s = pd.Series(d.values, index=key).groupby(level=0).last()
    return s[s.index.dayofweek < 5]


def fx_closes() -> pd.DataFrame:
    cols = {}
    for p in PAIRS:
        parts = [_daily_close("data_cache/combined/" + f.format(p)) for f in FX_FILES]
        s = pd.concat(parts)
        cols[p] = s[~s.index.duplicated(keep="last")].sort_index()
    return pd.DataFrame(cols).ffill()


def ccy_returns(closes: pd.DataFrame) -> pd.DataFrame:
    """Tagesrendite jeder Waehrung gegen USD (USD = 0)."""
    lr = np.log(closes).diff()
    out = pd.DataFrame({CCY[p]: (lr[p] if p.endswith("USD") else -lr[p]) for p in PAIRS})
    out["US"] = 0.0
    return out[CURRENCIES]


def rates(index: pd.DatetimeIndex, quantity: str) -> pd.DataFrame:
    """Zinsen in % je Waehrung, auf Handelstage vorgetragen (nur bekannte Werte)."""
    r = pd.read_parquet(RATES)
    r = r[r["key"].str.endswith("." + quantity)]
    wide = r.assign(ccy=r["key"].str.split(".").str[0]).pivot_table(index="date", columns="ccy", values="value")
    wide = wide.reindex(wide.index.union(index)).ffill().reindex(index)
    return wide[[c for c in CURRENCIES if c in wide.columns]]


def vix(index: pd.DatetimeIndex) -> pd.Series:
    r = pd.read_parquet(RATES)
    s = r[r["key"] == "MKT.vix"].set_index("date")["value"].sort_index()
    return s.reindex(s.index.union(index)).ffill().reindex(index)


def stats(ret: pd.Series) -> dict:
    ret = ret.dropna()
    sr_d = ret.mean() / ret.std() if ret.std() > 0 else 0.0
    eq = ret.cumsum()
    return {"n": len(ret), "ret_pa": ret.mean() * 252, "vol_pa": ret.std() * np.sqrt(252),
            "sharpe": sr_d * np.sqrt(252), "t": sr_d * np.sqrt(len(ret)), "sr_d": sr_d,
            "maxdd": (eq - eq.cummax()).min(), "skew": ret.skew(), "kurt": ret.kurt() + 3}
