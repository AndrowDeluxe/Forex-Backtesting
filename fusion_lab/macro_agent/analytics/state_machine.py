"""Zustand BASE / ALT / TAIL mit Zahlenschwellen ([[makro-wirkketten-und-regeln]] §6).

TAIL-Schwellen aus dem SMT-Report 21.10.2026; der OAT-Bund-Spread fehlt in der Datenschicht und
wird als n.v. gefuehrt (zaehlt nicht mit). ALT = eigene Annahme (10.11.2026, zur Bestaetigung).
"""

from __future__ import annotations

import pandas as pd

TAIL = [("vix", ">", 28.0), ("hy_spread", ">", 3.50), ("brent", ">", 120.0), ("oat_bund_bp", ">", 180.0)]
TAIL_MIN = 2
ALT = [("vix", "<", 16.0), ("hy_spread", "<", 3.00), ("brent", "<", 90.0)]
HAVEN = {"spx_ret_pct": -1.5, "vix": 24.0}
HAVEN_DAYS = 5


def _hit(value, op: str, threshold: float):
    if value is None or pd.isna(value):
        return None
    return value > threshold if op == ">" else value < threshold


def _conditions(rules, values: dict) -> list[dict]:
    return [{"name": n, "op": op, "threshold": t, "value": values.get(n), "hit": _hit(values.get(n), op, t)}
            for n, op, t in rules]


def evaluate(values: dict) -> dict:
    tail, alt = _conditions(TAIL, values), _conditions(ALT, values)
    if sum(c["hit"] is True for c in tail) >= TAIL_MIN:
        state = "TAIL"
    elif all(c["hit"] is True for c in alt):
        state = "ALT"
    else:
        state = "BASE"
    return {"state": state, "tail": tail, "alt": alt}


def safe_haven_days(dxy: pd.Series, spx: pd.Series, vix: pd.Series, days: int = HAVEN_DAYS) -> list[str]:
    """Tage, an denen der Dollar als Hafen lief: DXY steigt, S&P < −1,5 %, VIX > 24."""
    df = pd.DataFrame({"dxy": dxy.diff(), "spx": spx.pct_change() * 100, "vix": vix}).dropna().iloc[-days:]
    hit = (df["dxy"] > 0) & (df["spx"] < HAVEN["spx_ret_pct"]) & (df["vix"] > HAVEN["vix"])
    return [d.date().isoformat() for d in df.index[hit]]
