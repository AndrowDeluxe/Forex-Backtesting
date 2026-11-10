"""Zins-Momentum + Carry je Markt -- wiederverwendbarer Filter-Baustein (FX-Zinsschicht).

Schicht „Zinsen“ im Schichtenmodell ([[regime-bestimmung-und-filter]]); erster Einsatz im Test
C2 × Makro-Filter (Nutzerauftrag 10.11.2026, [[htf-daily-trade-edge-card]]).

Zins-Momentum: 2y-Spread Basis minus USD heute gegen vor `lag` Beobachtungen. Steigt er, ist nur
long in der Basiswaehrung erlaubt (USDJPY gespiegelt). Metalle: US-2y faellt = long.
Carry: 2y-Differenz Basis minus USD > 0 = long in der Basiswaehrung. Metalle: US-Realzins
(10y minus 10y-Breakeven) faellt ueber `lag` Beobachtungen = long.

Richtung: +1 nur long, −1 nur short, 0 keine Aussage (fehlende Daten, Differenz genau 0).
Alle Abfragen nutzen nur Werte mit Datum VOR dem abgefragten Tag.
Daten: fusion_lab/macro_data (2y-Renditen ab 2009, AU vor 09/2013 aus AU.2y_tvc; vor dem
30.10.2026 heutiger Revisionsstand).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.macro_data import store

# Markt -> (Land der Basiswaehrung, +1 wenn Basis gegen USD notiert, −1 wenn USD die Basis ist)
FX = {"EURUSD": ("EA", +1), "GBPUSD": ("GB", +1), "AUDUSD": ("AU", +1), "USDJPY": ("JP", -1)}
METALS = ("XAUUSD", "XAGUSD")


def _sign(x) -> int:
    return 0 if x is None or pd.isna(x) or x == 0 else int(np.sign(x))


class ZinsFxFilter:
    def __init__(self, lag: int = 20, data: pd.DataFrame | None = None):
        if data is None:
            data = store.latest("macro")
        self.lag = lag
        self.wide = data.pivot_table(index="date", columns="key", values="value").sort_index()
        # Ersatz-Historie (z. B. AU.2y_tvc) nur vor dem ersten Wert der Hauptreihe
        for alt in [c for c in self.wide.columns if c.endswith("_tvc")]:
            main = alt.removesuffix("_tvc")
            first = self.wide[main].first_valid_index() if main in self.wide else None
            fill = self.wide[alt] if first is None else self.wide[alt].loc[self.wide.index < first]
            self.wide[main] = self.wide.get(main, pd.Series(dtype=float)).combine_first(fill)

    def _hist(self, key: str, date) -> pd.Series:
        """Reihe bis zum Vortag (Werte mit Datum < date)."""
        s = self.wide[key].dropna() if key in self.wide else pd.Series(dtype=float)
        return s.loc[s.index < pd.Timestamp(date)]

    def _spread(self, country: str, date) -> pd.Series:
        a, b = self._hist(f"{country}.2y", date), self._hist("US.2y", date)
        return (a - b).dropna()

    def _change(self, s: pd.Series):
        return None if len(s) <= self.lag else s.iloc[-1] - s.iloc[-1 - self.lag]

    def momentum_dir(self, market: str, date) -> int:
        if market in METALS:
            return -_sign(self._change(self._hist("US.2y", date)))
        country, orient = FX[market]
        return orient * _sign(self._change(self._spread(country, date)))

    def carry_dir(self, market: str, date) -> int:
        if market in METALS:
            real = (self._hist("US.10y", date) - self._hist("US.breakeven_10y", date)).dropna()
            return -_sign(self._change(real))
        country, orient = FX[market]
        s = self._spread(country, date)
        return orient * _sign(s.iloc[-1] if len(s) else None)

    @staticmethod
    def state(direction: int, side: str) -> str:
        """dafuer / dagegen / neutral fuer eine Trade-Seite."""
        if direction == 0:
            return "neutral"
        return "dafuer" if (direction == 1) == (side == "long") else "dagegen"
