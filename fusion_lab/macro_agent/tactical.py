"""Taktische Ebene (1-4 Wochen): Notenbank-Pricing je Sitzung, Rohstoff-Schalter, Positionsaenderung.

Kein Backtest-Beleg als Signal: Kontext fuer den Agenten (Regel 3.1/3.2 aus
[[makro-wirkketten-und-regeln]], Leitlinie Gegenwaehrung aus [[makro-agent-report-pruefung]]).
"""

from __future__ import annotations

import pandas as pd

from .analytics.profiles import change, series
from .fed_meetings import meeting_path

# Waehrung -> (Rohstoff-Schluessel, Schwelle oder None). Brent 105 aus der Leitlinie (CAD, Hormus).
COMMODITY = {"AUD": ("MKT.copper", None), "CAD": ("MKT.brent", 105.0), "NZD": ("MKT.milk", None)}
PRICING_LANDS = ["EA", "GB", "JP", "CH", "AU", "CA", "NZ"]


def _r(v, d=4):
    return None if v is None or pd.isna(v) else round(float(v), d)


def fed(mkt_w: pd.DataFrame, macro_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Sitzungspfad heute und vor einer Woche (Regel 3.2: die Veraenderung ist das Signal)."""
    eff = series(macro_w, "US.fed_funds")
    keys = [k for k in mkt_w.columns if k.startswith("US.ff_implied.")]

    def path(day):
        implied = {}
        for k in keys:
            s = series(mkt_w, k)
            s = s[s.index <= day]
            if len(s):
                implied[k.rsplit(".", 1)[1]] = float(s.iloc[-1])
        e = eff[eff.index <= day]
        return meeting_path(implied, float(e.iloc[-1]), day) if len(e) and implied else []

    now, before = path(as_of), {p["sitzung"]: p for p in path(as_of - pd.Timedelta(days=7))}
    for p in now:
        prev = before.get(p["sitzung"])
        p["pct_vor_1w"] = prev["pct"] if prev else None
    return {"effektiv": _r(eff.iloc[-1]) if len(eff) else None, "sitzungen": now[:6]}


def other_pricing(macro_w: pd.DataFrame) -> dict:
    """Naeherung ohne OIS: 1J-Rendite minus Leitzins ~ gepreiste Aenderung der naechsten 12 Monate."""
    out = {}
    for land in PRICING_LANDS:
        y1, pol = series(macro_w, f"{land}.1y"), series(macro_w, f"{land}.policy_rate")
        if y1.empty or pol.empty:
            out[land] = None
            continue
        spread = (y1 - pol.reindex(y1.index, method="ffill")).dropna()
        out[land] = {"leitzins": _r(pol.iloc[-1]), "leitzins_datum": pol.index[-1].date().isoformat(),
                     "1y": _r(y1.iloc[-1]), "gepreist_12m_bp": _r(spread.iloc[-1] * 100, 1),
                     "chg_1w_bp": _r(None if change(spread, 5) is None else change(spread, 5) * 100, 1),
                     "datum": spread.index[-1].date().isoformat()}
    return out


def commodities(mkt_w: pd.DataFrame) -> dict:
    out = {}
    for ccy, (key, threshold) in COMMODITY.items():
        s = series(mkt_w, key)
        if len(s) < 61:
            out[ccy] = None
            continue
        pct = lambda n: float((s.iloc[-1] / s.iloc[-1 - n] - 1) * 100)
        node = {"rohstoff": key.split(".")[1], "kurs": _r(s.iloc[-1], 2), "datum": s.index[-1].date().isoformat(),
                "ret_20d_pct": _r(pct(20), 2), "ret_60d_pct": _r(pct(60), 2),
                "trend": "steigt" if pct(60) > 0 else "faellt"}
        if threshold is not None:
            node["schwelle"] = threshold
            node["abstand_pct"] = _r((s.iloc[-1] / threshold - 1) * 100, 2)
        out[ccy] = node
    return out
