"""Backtest des G8-Staerke-Scores als Querschnitts-Strategie (Phase 1, Schritt 4).

Signal am Tagesschluss t (FRED Noon Rates), Position ab t+1 (keine Ueberlappung
mit dem Signaltag). Long die k staerksten, short die k schwaechsten Waehrungen,
je 1/(2k) Gewicht; Ertrag = gewichtete Tages-Logrendite der Waehrungswerte in
USD (USD selbst = 0). Kosten: halbe Round-Trip-bps je Einheit Umschlag.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.g8.model import DEFAULT_NORM, score

COST_BPS_PER_UNIT = 1.25  # halbe Round-Trip (~2,5 bps Kreuzkurs) je Einheit |Δw|


def weights(sc: pd.DataFrame, k: int, rebalance: str) -> pd.DataFrame:
    rank = sc.rank(axis=1, ascending=False)
    n = sc.notna().sum(axis=1)
    w = (rank <= k).astype(float) - (rank > n.to_numpy()[:, None] - k).astype(float)
    w = w.where(sc.notna(), 0.0) / (2 * k)
    w[n < 8] = 0.0
    if rebalance == "weekly":  # nur am letzten Handelstag der Woche neu gewichten
        last_of_week = w.index.to_series().groupby(w.index.to_period("W")).transform("max") == w.index
        w = w.where(last_of_week).ffill().fillna(0.0)
    return w


def daily_returns(logv: pd.DataFrame, k: int, rebalance: str, norm: str = DEFAULT_NORM) -> pd.Series:
    sc, _ = score(logv, norm)
    w = weights(sc, k, rebalance)
    held = w.shift(1).fillna(0.0)                      # Signal t -> Position ab t+1
    gross = (held * logv.diff()).sum(axis=1)
    cost = held.diff().abs().sum(axis=1).fillna(0.0) * COST_BPS_PER_UNIT / 10_000
    return (gross - cost).iloc[64:]


def stats(r: pd.Series) -> dict:
    if len(r) < 20:
        return {"n_days": int(len(r))}
    ann = np.sqrt(252)
    eq = r.cumsum()
    return {
        "n_days": int(len(r)), "ann_ret_pct": round(float(r.mean() * 252 * 100), 2),
        "ann_vol_pct": round(float(r.std() * ann * 100), 2),
        "sharpe": round(float(r.mean() / r.std() * ann), 2) if r.std() > 0 else None,
        "max_dd_pct": round(float((eq.cummax() - eq).max() * 100), 2),
        "hit_years": f"{int((r.groupby(r.index.year).sum() > 0).sum())}/{r.index.year.nunique()}",
    }
