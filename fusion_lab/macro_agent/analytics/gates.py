"""Daten-Gates R/P/B/F je Markt und Seite ([[makro-wirkketten-und-regeln]] §4).

Gate M (Grund aus Wirtschaft/Notenbank) braucht Deutung und bleibt beim Agenten; die Regel
„mindestens 4 von 5 PASS, kein dominantes FAIL“ wendet erst er an.
Jedes Gate liefert PASS / FAIL / n.v. und die Zahl dahinter. Schwellen = eigene Annahmen
(10.11.2026, Dashboard „Braucht deine Bestaetigung“).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .profiles import change, series

R_OBS = 5           # Wochenveraenderung (Regel 3.2: die Veraenderung ist das Signal)
COT_CROWDED = 90    # COT-Index 3 J: ab hier ist eine Seite ueberlaufen (unten 100 - 90)
CCY_COUNTRY = {"USD": "US", "EUR": "EA", "GBP": "GB", "JPY": "JP", "CHF": "CH", "AUD": "AU",
               "CAD": "CA", "NZD": "NZ"}
SIDES = {"long": 1, "short": -1}


def _sign(x) -> int:
    return 0 if x is None or pd.isna(x) or x == 0 else int(np.sign(x))


def legs(market: str) -> tuple[str, str]:
    return market[:3], market[3:6]


def rates_direction(market: str, macro_w: pd.DataFrame) -> dict:
    """+1 = Zinsen sprechen fuer long. Je Bein die eigene Wochenveraenderung, damit ein Land mit
    Verzug (CH ~10 Tage) das andere nicht auf ein altes gemeinsames Datum zieht."""
    base, quote = legs(market)
    if base == "XAU":
        real = (series(macro_w, "US.10y") - series(macro_w, "US.breakeven_10y")).dropna()
        chg = change(real, R_OBS)
        chg = None if chg is None else round(chg * 100, 1)
        return {"dir": -_sign(chg), "basis": "US-Realzins 10J", "chg_bp": chg}
    cb, cq = (change(series(macro_w, f"{CCY_COUNTRY[c]}.2y"), R_OBS) for c in (base, quote))
    if cb is None or cq is None:
        return {"dir": None, "basis": "2J-Spread", "chg_bp": None}
    chg = round((cb - cq) * 100, 1)  # Vorzeichen vom gerundeten Wert: −5,0 − (−5,0) ist keine Bewegung
    return {"dir": _sign(chg), "basis": "2J-Spread", "chg_bp": chg,
            "base_chg_bp": round(cb * 100, 1), "quote_chg_bp": round(cq * 100, 1)}


def price_direction(st: dict | None) -> dict:
    if not st:
        return {"dir": None}
    above, up = st["dist_sma20_pct"] > 0, st["ret_5d_pct"] > 0
    d = 1 if above and up else -1 if not above and not up else 0
    return {"dir": d, "dist_sma20_pct": st["dist_sma20_pct"], "ret_5d_pct": st["ret_5d_pct"]}


def g8_direction(market: str, g8: pd.Series | None) -> dict:
    base, quote = legs(market)
    if g8 is None or base not in g8 or quote not in g8:
        return {"dir": None}
    diff = float(g8[base] - g8[quote])
    return {"dir": _sign(diff), "diff": round(diff, 2)}


def crowding(market: str, pos: dict) -> dict:
    """COT-Index 3 J je Bein. Gold: Managed Money auf Gold allein."""
    base, quote = legs(market)
    get = lambda name: (pos.get(name) or {}).get("cot_3y")
    if base == "XAU":
        return {"base": get("GOLD"), "quote": None}
    return {"base": get(base), "quote": get(quote)}


def _result(direction, side: int) -> str:
    if direction is None:
        return "n.v."
    return "PASS" if direction == side else "FAIL"


def f_result(c: dict, side: int) -> str:
    """FAIL, wenn unsere Seite schon ueberlaufen ist: long = Basis oben oder Quote unten."""
    b, q = c["base"], c["quote"]
    if b is None and q is None:
        return "n.v."
    hi, lo = COT_CROWDED, 100 - COT_CROWDED
    if side == 1:
        crowded = (b is not None and b >= hi) or (q is not None and q <= lo)
    else:
        crowded = (b is not None and b <= lo) or (q is not None and q >= hi)
    return "FAIL" if crowded else "PASS"


def evaluate(market: str, st: dict | None, macro_w: pd.DataFrame, g8: pd.Series | None, pos: dict) -> dict:
    inputs = {"R": rates_direction(market, macro_w), "P": price_direction(st), "B": g8_direction(market, g8),
              "F": crowding(market, pos)}
    sides = {}
    for name, side in SIDES.items():
        res = {g: _result(inputs[g]["dir"], side) for g in ("R", "P", "B")}
        res["F"] = f_result(inputs["F"], side)
        sides[name] = {**res, "pass": sum(v == "PASS" for v in res.values()),
                       "verfuegbar": sum(v != "n.v." for v in res.values())}
    return {"inputs": inputs, **sides}
