"""Strategische Ebene (1-3 Monate): fuenf Faktoren je Waehrung, gleich gewichtet zum Score.

Nutzerentscheid 11.11.2026: Faktoren fest und gleich gewichtet, keine Gewichtsoptimierung.
Belege je Faktor: knowledge/resources/makro-gates-evidenz.md. Jeder Faktor ist ein Querschnitts-
z-Wert ueber die 8 Waehrungen am selben Tag (mindestens MIN_LANDS Werte, sonst fehlt er an dem Tag).

Positions-Veto ohne USD: Die Legacy-COT-Historie (ab 2000) kennt den Dollar-Index-Kontrakt nicht;
damit Backtest und Live gleich rechnen, gilt das Veto nur fuer die sieben anderen Waehrungen.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.macro_data.sources import cot_index

from .panels import LANDS, Panels, _on_days

FACTORS = ["carry", "zins_momentum", "preis_momentum", "value", "ueberraschung"]
MIN_LANDS = 4
MIN_FACTORS = 3
Z_CLIP = 3.0
RATE_MOM_DAYS = 63          # 3 Monate
MOM_LONG, MOM_SKIP, MOM_SHORT = 252, 21, 63   # 12-1 Monate und 3 Monate
VALUE_MONTHS = 120          # REER gegen eigenes 10-J-Mittel
SURPRISE_DAYS = 60
COT_WEEKS = 156
COT_HI, COT_LO = 90.0, 10.0


def xs_z(raw: pd.DataFrame) -> pd.DataFrame:
    """Querschnitts-z je Tag; Tage mit weniger als MIN_LANDS Werten bleiben leer."""
    n = raw.notna().sum(axis=1)
    z = raw.sub(raw.mean(axis=1), axis=0).div(raw.std(axis=1, ddof=1), axis=0)
    return z.where(n >= MIN_LANDS).clip(-Z_CLIP, Z_CLIP)


def raw_factors(p: Panels, days: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    policy = _on_days(p.policy, days)
    y2 = _on_days(p.y2, days)
    value = p.value.reindex(days).ffill()
    reer = p.reer.rolling(VALUE_MONTHS, min_periods=VALUE_MONTHS // 2).mean()
    reer_gap = _on_days(p.reer - reer, days)
    sur = p.surprise.reindex(p.surprise.index.union(days)).fillna(0.0)
    sur = sur.rolling(f"{SURPRISE_DAYS}D").sum().reindex(days)
    sur = sur.where(_on_days(p.surprise.notna().cumsum().clip(upper=1).replace(0, np.nan), days).notna())
    return {
        "carry": policy,
        "zins_momentum": y2 - y2.shift(RATE_MOM_DAYS),
        "preis_momentum": 0.5 * (value.shift(MOM_SKIP) - value.shift(MOM_LONG)) + 0.5 * (value - value.shift(MOM_SHORT)),
        "value": -reer_gap,
        "ueberraschung": sur,
    }


def cot_indices(p: Panels, days: pd.DatetimeIndex) -> pd.DataFrame:
    idx = pd.DataFrame({c: cot_index(p.cot[c].dropna(), COT_WEEKS) for c in p.cot.columns})
    return _on_days(idx, days).reindex(columns=LANDS)


def scorecard(p: Panels, days: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    """z je Faktor, Score (Mittel der vorhandenen Faktoren), COT-Index und Veto-Flags."""
    z = {k: xs_z(v.reindex(columns=LANDS)) for k, v in raw_factors(p, days).items()}
    stack = np.stack([z[k].to_numpy() for k in FACTORS])
    count = np.sum(~np.isnan(stack), axis=0)
    score = pd.DataFrame(np.where(count >= MIN_FACTORS, np.nanmean(stack, axis=0), np.nan),
                         index=days, columns=LANDS)
    cot = cot_indices(p, days)
    return {**z, "score": score, "cot_3y": cot, "veto_long": cot >= COT_HI, "veto_short": cot <= COT_LO}


def month_end_weights(sc: dict[str, pd.DataFrame], k: int = 2, veto: bool = True) -> pd.DataFrame:
    """Monatsende: long die k staerksten, short die k schwaechsten Waehrungen (je Seite Summe 1).
    Ein Veto setzt die betroffene Seite dieser Waehrung auf 0 (kein Nachruecken)."""
    score = sc["score"]
    ends = score.groupby(score.index.to_period("M")).tail(1).index
    rows = {}
    for d in ends:
        row = score.loc[d].dropna()
        w = pd.Series(0.0, index=LANDS)
        if len(row) >= 2 * k:
            order = row.sort_values(kind="stable")
            low, high = order.index[:k], order.index[-k:]
            w[high], w[low] = 1.0 / k, -1.0 / k
            if veto:
                w[[c for c in high if sc["veto_long"].loc[d, c]]] = 0.0
                w[[c for c in low if sc["veto_short"].loc[d, c]]] = 0.0
        rows[d] = w
    return pd.DataFrame(rows).T


def pair_view(sc: dict[str, pd.DataFrame], day, base: str, quote: str) -> dict:
    """Score-Differenz eines Paares am Tag (Basis minus Quote) und Veto je Seite."""
    s = sc["score"].loc[day]
    diff = s.get(base, np.nan) - s.get(quote, np.nan)
    vl = bool(sc["veto_long"].loc[day].get(base, False) or sc["veto_short"].loc[day].get(quote, False))
    vs = bool(sc["veto_short"].loc[day].get(base, False) or sc["veto_long"].loc[day].get(quote, False))
    return {"diff": None if pd.isna(diff) else round(float(diff), 2), "veto_long": vl, "veto_short": vs}
