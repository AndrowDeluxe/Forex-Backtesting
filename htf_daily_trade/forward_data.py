"""Tageskerzen fuer den C2-Forward-Test: Backtest-Historie + Data Lake (Nutzerauftrag 11.11.2026).

Die Backtest-Dateien (data_cache/combined/*_D1_*) sind eingefroren (FX bis 09.10.2026, Gold 12.08.,
Silber 31.07.). Danach kommen Tageskerzen aus den Intraday-Bars des Data Lake (Dukascopy, UTC),
gebuendelt wie ipda_cycles.load_daily: UTC-Tag, Sonntag in den Montag, Samstag in den Freitag.
Nur abgeschlossene Tage: ein Tag zaehlt, wenn es danach schon Bars gibt oder er ein Freitag vor heute ist.
"""

from __future__ import annotations

import pandas as pd

from data_lake.storage import read_bars
from htf_daily_trade.backtest_r import load_market

LAKE = {"EURUSD": ("EURUSD", "M5"), "GBPUSD": ("GBPUSD", "M15"), "AUDUSD": ("AUDUSD", "M15"),
        "USDJPY": ("USDJPY", "M15"), "XAUUSD": ("GOLD", "H1"), "XAGUSD": ("SILVER", "H1")}


def daily_from_intraday(bars: pd.DataFrame, today: pd.Timestamp | None = None) -> pd.DataFrame:
    idx = bars.index.tz_convert("UTC").tz_localize(None) if bars.index.tz is not None else bars.index
    b = bars.set_axis(idx)
    key = idx.normalize()
    dow = idx.dayofweek
    key = key.where(dow != 6, key + pd.Timedelta(days=1))   # So -> Mo
    key = key.where(dow != 5, key - pd.Timedelta(days=1))   # Sa -> Fr
    g = b.groupby(key)
    d = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(),
                      "Low": g["Low"].min(), "Close": g["Close"].last()})
    d = d[d.index.dayofweek < 5]
    today = (today or pd.Timestamp.now("UTC").tz_localize(None)).normalize()
    last_bar_day = idx.max().normalize()
    done = (d.index < last_bar_day) | ((d.index.dayofweek == 4) & (d.index < today))
    return d[done & (d.index < today)]


def load_market_forward(name: str, today: pd.Timestamp | None = None) -> pd.DataFrame:
    hist = load_market(name)
    key, tf = LAKE[name]
    lake = read_bars("dukascopy", key, tf)
    if lake is None or lake.empty:
        return hist
    new = daily_from_intraday(lake[["Open", "High", "Low", "Close"]], today)
    return pd.concat([hist, new[new.index > hist.index.max()]]).sort_index()
