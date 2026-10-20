"""Regime-Logik (Regeln aus dem Original, Seite 2-3):

  1. Ist die YoY-Rate positiv oder negativ?           -> Vorzeichen (up/down)
  2. Steigt oder faellt sie gegenueber dem Vorprint?  -> accel/slow

Jeder Print (= jede neue ALFRED-Vintage) setzt den Zustand ab der FOLGENDEN
Sitzung. Drei Linsen: "signs" (nur 1), "change" (nur 2), "joint" (1 x 2).

Offen im Original ist, was "Vorprint" bei BIP-Revisionen heisst (2./3.
Schaetzung). Zwei Lesarten, per Kalibrierung gegen die Tageszahlen im PDF
gewaehlt (siehe CHANGE_RULES):
  "period":  YoY der juengsten Periode vs. YoY der Vorperiode, beide aus
             derselben Vintage (Q2 vs. Q1, so wie in der PDF-Tabelle).
  "print":   YoY des aktuellen Prints vs. YoY des vorigen Prints derselben
             Reihe (bei BIP-Revisionen also Revisionsrichtung).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import MACRO_SERIES, fetch_vintages

LAGS = {"growth": 4, "inflation": 12}  # Quartale / Monate fuer YoY
CHANGE_RULES = ("period", "print")
DEFAULT_CHANGE_RULE = "period"
SAMPLE_START = "1994-03-01"
LENSES = ("joint", "change", "signs")


def prints(kind: str, refresh: bool = False) -> pd.DataFrame:
    """Je Vintage: juengste Periode, deren YoY und die YoY der Vorperiode."""
    v = fetch_vintages(MACRO_SERIES[kind], refresh)
    lag = LAGS[kind]
    rows = []
    for vd in np.sort(v["realtime_start"].unique()):
        snap = v[(v["realtime_start"] <= vd) & (v["realtime_end"] >= vd)]
        s = snap.set_index("date")["value"].sort_index()
        if len(s) < lag + 2:
            continue
        yoy = (s / s.shift(lag) - 1) * 100
        rows.append({"release": pd.Timestamp(vd), "period": s.index[-1],
                     "yoy": yoy.iloc[-1], "yoy_prev_period": yoy.iloc[-2]})
    df = pd.DataFrame(rows).dropna()
    df["yoy_prev_print"] = df["yoy"].shift(1)
    return df.dropna().reset_index(drop=True)


def classify(p: pd.DataFrame, rule: str = DEFAULT_CHANGE_RULE) -> pd.DataFrame:
    prev = p["yoy_prev_period"] if rule == "period" else p["yoy_prev_print"]
    out = p.copy()
    out["up"] = p["yoy"] > 0
    out["accel"] = p["yoy"] > prev
    return out


def daily_labels(days: pd.DatetimeIndex, rule: str = DEFAULT_CHANGE_RULE,
                 refresh: bool = False) -> pd.DataFrame:
    """Zustand je Handelstag: letzter Print mit Release-Datum VOR dem Tag."""
    parts = {}
    days = pd.DatetimeIndex(days).astype("datetime64[ns]")
    for kind in MACRO_SERIES:
        c = classify(prints(kind, refresh), rule)
        c["release"] = c["release"].astype("datetime64[ns]")
        c = c.set_index("release")
        # Release am Tag X gilt ab X+1 -> merge_asof mit allow_exact_matches=False
        m = pd.merge_asof(pd.DataFrame(index=days).rename_axis("day").reset_index(),
                          c[["up", "accel", "yoy"]].reset_index(),
                          left_on="day", right_on="release", allow_exact_matches=False)
        parts[kind] = m.set_index("day")
    g, i = parts["growth"], parts["inflation"]
    lab = pd.DataFrame(index=days)
    lab["g_yoy"], lab["pi_yoy"] = g["yoy"], i["yoy"]
    lab["g_up"], lab["g_accel"] = g["up"], g["accel"]
    lab["pi_up"], lab["pi_accel"] = i["up"], i["accel"]
    lab = lab.dropna()
    arrow = lambda b: "↑" if b else "↓"
    speed = lambda b: "accel" if b else "slow"
    lab["signs"] = [f"g{arrow(a)} π{arrow(b)}" for a, b in zip(lab["g_up"], lab["pi_up"])]
    lab["change"] = [f"g{arrow(a)} π{arrow(b)}" for a, b in zip(lab["g_accel"], lab["pi_accel"])]
    lab["joint"] = [f"g{arrow(a)}·{speed(b)} × π{arrow(c)}·{speed(d)}"
                    for a, b, c, d in zip(lab["g_up"], lab["g_accel"], lab["pi_up"], lab["pi_accel"])]
    return lab


def regime_stats(excess: pd.DataFrame, labels: pd.DataFrame, lens: str) -> pd.DataFrame:
    """Je Regime und Asset: Tage, Rendite % p.a., Vola % p.a., Sharpe (alles vs. Cash)."""
    df = excess.join(labels[[lens]], how="inner")
    g = df.groupby(lens)
    mean, sd = g.mean() * 252 * 100, g.std() * np.sqrt(252) * 100
    out = pd.concat({"ret": mean, "vol": sd, "sharpe": mean / sd}, axis=1)
    out[("days", "n")] = g.size()
    return out.sort_values(("days", "n"), ascending=False)
