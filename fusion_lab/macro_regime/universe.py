"""Erweitertes Asset-Universum fuer die Regimekarte (Nutzerwunsch 28.10.2026):
zusaetzlich zu den Original-Assets die G8-FX-Paare, Silber und weitere Indizes.

  FX:      FRED H.10 Tageskurse (fusion_lab.g8.data), Paarrendite aus den USD-
           Werten der beiden Waehrungen. OHNE Carry (Zinsdifferenz fehlt) --
           Paarrenditen sind reine Kursrenditen, nicht Excess-Renditen.
  Metalle: Silber SI=F (yfinance, Front-Monat, ungerollt wie Gold im Original).
  Indizes: Nasdaq 100 ^NDX, Dow ^DJI, DAX ^GDAXI (Preisindizes ohne Dividenden).
Alle Reihen auf SPX-Handelstagen; Original-Assets bleiben Excess vs. Cash.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.g8.data import usd_value_panel

from .data import _cached, asset_excess_returns

EXTRA_YF = {"Silver": "SI=F", "NDX": "^NDX", "DJI": "^DJI", "DAX": "^GDAXI"}
# Paar -> (Basis, Quote); Rendite = log(Basis in USD) - log(Quote in USD)
FX_PAIRS = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"), "USDJPY": ("USD", "JPY"), "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"), "EURGBP": ("EUR", "GBP"), "EURJPY": ("EUR", "JPY"),
    "AUDNZD": ("AUD", "NZD"), "EURCHF": ("EUR", "CHF"), "GBPJPY": ("GBP", "JPY"),
    "AUDJPY": ("AUD", "JPY"), "EURAUD": ("EUR", "AUD"),
}
GROUPS = {
    "FX-Majors": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD"],
    "FX-Kreuze": ["EURGBP", "EURJPY", "AUDNZD", "EURCHF", "GBPJPY", "AUDJPY", "EURAUD"],
    "Metalle": ["Gold", "Silver", "Copper"],
    "Indizes": ["SPX", "NDX", "DJI", "DAX"],
    "Sonstige": ["UST", "Crude", "Wheat", "DXY"],
}


def fetch_extra_yf(refresh: bool = False) -> pd.DataFrame:
    def build():
        import yfinance as yf
        cols = {}
        for name, ticker in EXTRA_YF.items():
            d = yf.download(ticker, start="1990-01-01", progress=False, auto_adjust=True)
            cols[name] = d["Close"].squeeze()
        df = pd.DataFrame(cols)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df
    return _cached("yf_prices_extra", refresh, build)


def fx_pair_returns(refresh: bool = False) -> pd.DataFrame:
    lv = np.log(usd_value_panel("fred", force_refresh=refresh))
    return pd.DataFrame({p: (lv[b] - lv[q]).diff() for p, (b, q) in FX_PAIRS.items()})


def universe_returns(refresh: bool = False) -> pd.DataFrame:
    base = asset_excess_returns(refresh)
    px = fetch_extra_yf(refresh)
    extra = px.pct_change().where((px > 0) & (px.shift(1) > 0))
    fx = np.expm1(fx_pair_returns(refresh))
    out = base.join(extra.reindex(base.index)).join(fx.reindex(base.index))
    order = [a for g in GROUPS.values() for a in g]
    return out[[c for c in order if c in out.columns]]
