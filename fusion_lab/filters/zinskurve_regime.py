"""Zinskurven-Regime nach Angelo + Gold-Filter -- wiederverwendbarer Filter-Baustein.

Schicht „Zinsen“ im Schichtenmodell ([[regime-bestimmung-und-filter]], Nutzerentscheid 02.11.2026).
Beschreibung, Belege und Prüfprotokoll: knowledge/areas/filter-gold-zinskurve.md.

Regime (OneNote „Elite 2 / Makro Angelo / Zusammenfassung Regime“): US 10y−2y-Spread, 2y und 10y
heute gegen vor `lag` Handelstagen. Spread steigt = Steepener, fällt = Flattener; beide Renditen
fallen = Bull, steigen = Bear; gegenläufig = Twist.
Bull Flattener = Goldilocks, Bear Steepener = Reflation, Bear Flattener = Inflation,
Bull Steepener = Deflation.

Geglättet („bestätigt“): ein neues Regime gilt erst, wenn es `confirm` Tage in Folge besteht; Twist
und unbestätigte Wechsel lassen das letzte bestätigte Regime stehen.

Gold-Richtung (Dennis' Risk Regime Matrix): Goldilocks/Reflation long, Inflation short,
Deflation ohne Angabe (beide erlaubt).

Alle Abfragen nutzen nur Daten bis zum Vortag des abgefragten Datums (FRED-Schlusskurse).
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.g8.data import fetch_fred

GOLD_DIR = {"Goldilocks": 1, "Reflation": 1, "Inflation": -1, "Deflation": 0}


def regime_series(lag: int = 20, refresh: bool = False) -> pd.Series:
    """Rohes Tagesregime (inkl. „Twist“) je FRED-Datum."""
    y2, y10 = fetch_fred("DGS2", refresh), fetch_fred("DGS10", refresh)
    df = pd.DataFrame({"y2": y2, "y10": y10}).dropna()
    df["spread"] = df["y10"] - df["y2"]
    d = df - df.shift(lag)
    steep, flat = d["spread"] > 0, d["spread"] < 0
    bull = (d["y2"] < 0) & (d["y10"] < 0)
    bear = (d["y2"] > 0) & (d["y10"] > 0)
    reg = pd.Series("Twist", index=df.index, dtype=object)
    reg[bull & flat] = "Goldilocks"
    reg[bear & steep] = "Reflation"
    reg[bear & flat] = "Inflation"
    reg[bull & steep] = "Deflation"
    reg[d["spread"].isna()] = None
    return reg.dropna()


def confirmed(reg: pd.Series, confirm: int = 5) -> pd.Series:
    """Regime erst nach `confirm` Tagen Bestand; Twist zählt nie als Bestätigung."""
    runs = (reg != reg.shift()).cumsum()
    age = reg.groupby(runs).cumcount() + 1
    ok = (age >= confirm) & (reg != "Twist")
    return reg.where(ok).ffill()


class GoldZinskurvenFilter:
    """Erlaubte Gold-Richtung je Datum: +1 nur long, −1 nur short, 0 beide."""

    def __init__(self, lag: int = 20, confirm: int = 5, refresh: bool = False):
        self.regime = confirmed(regime_series(lag, refresh), confirm)

    def regime_at(self, date) -> str | None:
        i = self.regime.index.searchsorted(pd.Timestamp(date), side="left") - 1
        return None if i < 0 else self.regime.iloc[i]

    def direction(self, date) -> int:
        r = self.regime_at(date)
        return 0 if r is None or pd.isna(r) else GOLD_DIR[r]

    def allows(self, side: str, date) -> bool:
        d = self.direction(date)
        return d == 0 or (d == 1) == (side == "long")
