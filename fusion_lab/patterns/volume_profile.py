"""Tages-Volumenprofile (POC, Value Area) und Delta-Naeherung aus Intraday-Kerzen -- Baustein.

Quelle: Dennis (Elite Coaching), [[smh-dennis-volumen-ltf-inducement-day]]. Erster Einsatz:
scripts/research_dennis_inducement_day.py (Plan 24.11.2026).

Tag = CME-Handelstag (17:00 Chicago bis 17:00 Chicago, Label = Datum des Sitzungsendes).
Profil: Volumen jeder Kerze gleichmaessig auf die Preis-Bins zwischen Low und High verteilt, festes
Raster `step` (FX 1 Pip, Gold 0,50 $). Value Area wie auction_playbook/indicators.py::value_area
(vom POC aus jeweils den volumenstaerkeren Nachbar-Bin dazunehmen, bis `pct` erreicht ist).
Volumen = Dukascopy-Tick-Volumen (Ersatz fuer Futures-Volumen).

Delta-Naeherung wie TradingViews „Volume Delta“: Volumen steigender Kerzen = Kauf, fallender = Verkauf.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VA_PCT = 0.70


def cme_day(index: pd.DatetimeIndex) -> np.ndarray:
    """CME-Handelstag je Zeitstempel (UTC-Index) als datetime64[D]."""
    chi = index.tz_convert("America/Chicago").tz_localize(None)
    day = (chi + pd.Timedelta(hours=7)).normalize()
    # Spot-Wochenstart (So 22:00 UTC) liegt vor der CME-Eroeffnung: Sonntag gehoert zum Montag
    day = day + pd.to_timedelta((day.dayofweek == 6).astype(int), unit="D")
    return day.to_numpy().astype("datetime64[D]")


class Histogram:
    """Laufendes Profil eines Tages; Bins absolut als floor(preis / step)."""

    def __init__(self, lo: float, hi: float, step: float):
        self.step = step
        self.base = int(np.floor(lo / step))
        self.v = np.zeros(int(np.floor(hi / step)) - self.base + 1)

    def add(self, low: float, high: float, vol: float) -> None:
        a = int(np.floor(low / self.step)) - self.base
        b = int(np.floor(high / self.step)) - self.base
        self.v[a:b + 1] += vol / (b - a + 1)

    def price(self, i: int) -> float:
        return (self.base + i + 0.5) * self.step

    def poc_va(self, pct: float = VA_PCT) -> tuple[float, float, float]:
        """(VAL, POC, VAH)."""
        v = self.v
        tot = v.sum()
        if tot <= 0:
            return (np.nan, np.nan, np.nan)
        p = int(v.argmax())
        lo = hi = p
        inc = v[p]
        while inc < tot * pct and (lo > 0 or hi < len(v) - 1):
            below = v[lo - 1] if lo > 0 else -1.0
            above = v[hi + 1] if hi < len(v) - 1 else -1.0
            if above >= below:
                hi += 1
                inc += v[hi]
            else:
                lo -= 1
                inc += v[lo]
        return (self.price(lo), self.price(p), self.price(hi))


def day_profiles(bars: pd.DataFrame, step: float, pct: float = VA_PCT) -> pd.DataFrame:
    """Abgeschlossene Tagesprofile: je CME-Tag Open/High/Low/Close, VAL/POC/VAH, Volumen."""
    days = cme_day(bars.index)
    o, h, l, c, v = (bars[k].to_numpy() for k in ("Open", "High", "Low", "Close", "Volume"))
    rows = []
    starts = np.r_[0, np.flatnonzero(days[1:] != days[:-1]) + 1, len(days)]
    for a, b in zip(starts[:-1], starts[1:]):
        hist = Histogram(l[a:b].min(), h[a:b].max(), step)
        for i in range(a, b):
            hist.add(l[i], h[i], v[i])
        val, poc, vah = hist.poc_va(pct)
        rows.append({"day": days[a], "open": o[a], "high": h[a:b].max(), "low": l[a:b].min(), "close": c[b - 1],
                     "val": val, "poc": poc, "vah": vah, "volume": v[a:b].sum(), "bars": b - a})
    return pd.DataFrame(rows).set_index("day")


def bar_delta(bars: pd.DataFrame) -> pd.Series:
    """Volumen mit Vorzeichen der Kerze (Schluss > Open = Kauf, < Open = Verkauf, gleich = 0)."""
    return np.sign(bars["Close"] - bars["Open"]) * bars["Volume"]
