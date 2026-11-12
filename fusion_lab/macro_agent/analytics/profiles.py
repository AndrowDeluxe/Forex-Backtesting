"""Laenderprofile, Fed-Pfad und Positionierung aus der Datenschicht (fusion_lab/macro_data).

Alle Funktionen bekommen bereits auf den Stand gefilterte Daten (Werte mit Datum <= as_of).
Veraenderungen zaehlen Beobachtungen, nicht Kalendertage: chg_5d = eine Handelswoche.
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.macro_data.__main__ import COVERAGE
from fusion_lab.macro_data.sources import G8, cot_index

QUANTITIES = ["policy_rate", "1y", "2y", "10y", "cpi_yoy", "core_yoy", "services_yoy", "unemployment",
              "gdp_qoq", "trade_balance"]
DAILY = {"policy_rate", "1y", "2y", "10y"}
FED_MONTHS = 8
# CFTC-Schluessel -> Netto-Spalte; Gold ueber Managed Money, Waehrungen ueber Leveraged Funds
POSITIONING = {**{c: f"{c}.lev_net" for c in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]},
               "GOLD": "GOLD.mm_net"}


def wide(long: pd.DataFrame) -> pd.DataFrame:
    return long.pivot_table(index="date", columns="key", values="value").sort_index()


def series(w: pd.DataFrame, key: str) -> pd.Series:
    # leere Reihe mit Datumsindex: Vergleiche wie s.index <= Tag duerfen nicht scheitern (--as-of vor 30.10.)
    return w[key].dropna() if key in w else pd.Series(dtype=float, index=pd.DatetimeIndex([]))


def change(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return None if len(s) <= n else float(s.iloc[-1] - s.iloc[-1 - n])


def _r(v, digits: int = 4):
    return None if v is None or pd.isna(v) else round(float(v), digits)


def _bp(v):
    """Prozentpunkte -> Basispunkte, damit der Report keine umgerechnete Zahl nennen muss."""
    return None if v is None else round(v * 100, 1)


def country_profile(w: pd.DataFrame, land: str, as_of: pd.Timestamp) -> dict:
    out = {}
    for q in QUANTITIES:
        s = series(w, f"{land}.{q}")
        if s.empty:
            out[q] = None
            continue
        node = {"value": _r(s.iloc[-1]), "date": s.index[-1].date().isoformat(),
                "stale": (as_of - s.index[-1]).days > COVERAGE.get(q, 135)}
        if q in DAILY:
            node["chg_5d_bp"] = _bp(change(s, 5))
            node["chg_20d_bp"] = _bp(change(s, 20))
        out[q] = node
    y1, y2, y10, policy = (series(w, f"{land}.{q}") for q in ("1y", "2y", "10y", "policy_rate"))
    if len(y2) and len(y10):
        curve = (y10 - y2).dropna()
        out["curve_10y_2y"] = {"value": _r(curve.iloc[-1]), "chg_5d_bp": _bp(change(curve, 5)),
                               "date": curve.index[-1].date().isoformat()} if len(curve) else None
    short, basis = (y1, "1J") if len(y1) else (y2, "2J")
    if len(short) and len(policy):
        # Naeherung fuers Zinspricing ohne OIS: 1J (sonst 2J) ueber dem Leitzins = Anhebungen gepreist
        spread = (short - policy.reindex(short.index, method="ffill")).dropna()
        out["pricing"] = {"value": _r(spread.iloc[-1]), "chg_5d_bp": _bp(change(spread, 5)), "basis": basis,
                          "date": spread.index[-1].date().isoformat()} if len(spread) else None
    return out


def profiles(w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    return {land: country_profile(w, land, as_of) for land in G8}


def fed_path(markets_w: pd.DataFrame, macro_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Implizierter Fed-Funds-Satz je Liefermonat; priced_bp = Abstand zum effektiven Satz."""
    eff = series(macro_w, "US.fed_funds")
    effective = float(eff.iloc[-1]) if len(eff) else None
    months = {}
    keys = sorted(k for k in markets_w.columns if k.startswith("US.ff_implied."))
    for key in keys:
        month = key.rsplit(".", 1)[1]
        if month < as_of.strftime("%Y-%m"):
            continue
        s = series(markets_w, key)
        if s.empty:
            continue
        months[month] = {"implied": _r(s.iloc[-1]), "date": s.index[-1].date().isoformat(),
                         "priced_bp": _bp(s.iloc[-1] - effective) if effective is not None else None,
                         "chg_5d_bp": _bp(change(s, 5))}
        if len(months) == FED_MONTHS:
            break
    return {"effective": _r(effective), "months": months}


def positioning(pos_w: pd.DataFrame) -> dict:
    out = {}
    for name, key in POSITIONING.items():
        s = series(pos_w, key)
        if s.empty:
            out[name] = None
            continue
        out[name] = {"net": _r(s.iloc[-1], 0), "chg_1w": _r(change(s, 1), 0),
                     "cot_26w": _r(cot_index(s, 26).iloc[-1], 1), "cot_3y": _r(cot_index(s, 156).iloc[-1], 1),
                     "date": s.index[-1].date().isoformat()}
    return out
