"""Schwellen ohne Blick auf den Bruch.

Unter "Edge intakt" werden die Trades des Kalibrierfensters mit
Zuruecklegen gezogen (Bootstrap, iid). Auf jedem simulierten Pfad wird die
Badness berechnet; die Schwelle wird so gesetzt, dass im Mittel hoechstens
`budget` Fehlalarm-Episoden je Jahr entstehen. Freigabe (Hysterese) liegt
auf halbem Weg zwischen dem Normalwert (Median unter H0) und der Schwelle.
"""
from __future__ import annotations

import numpy as np

from edge_monitor import signals
from edge_monitor.switch import episodes_seq

N_PATHS = 300
YEARS = 5
BUDGETS = {"streng": 1 / 5, "locker": 1 / 2}   # Fehlalarme je Jahr


def reference(r_cal: np.ndarray) -> tuple[float, float, int]:
    return float(np.mean(r_cal)), float(np.std(r_cal, ddof=1)), len(r_cal)


def thresholds(r_cal: np.ndarray, trades_per_year: float, seed: int = 7) -> dict:
    """{signal: {budget_name: (thr, rel)}} aus dem Kalibrierfenster."""
    mu0, sd0, n0 = reference(r_cal)
    rng = np.random.default_rng(seed)
    L = max(50, int(round(trades_per_year * YEARS)))
    paths = rng.choice(r_cal, size=(N_PATHS, L), replace=True)
    out = {}
    for name in signals.SIGNALS:
        bs = [signals.compute(name, p, mu0, sd0, n0) for p in paths]
        allv = np.concatenate([b[~np.isnan(b)] for b in bs])
        b0 = float(np.median(allv))
        cand = np.unique(np.quantile(allv, np.linspace(0.5, 0.9999, 400)))
        res = {}
        for bname, budget in BUDGETS.items():
            target = budget * YEARS
            def eps_at(i):
                thr = cand[i]
                return np.mean([episodes_seq(b, thr, b0 + (thr - b0) / 2) for b in bs])
            lo, hi = 0, len(cand) - 1     # Bisektion: kleinste Schwelle mit Episoden <= Budget
            while lo < hi:
                mid = (lo + hi) // 2
                if eps_at(mid) <= target:
                    hi = mid
                else:
                    lo = mid + 1
            thr = float(cand[lo])
            res[bname] = (thr, float(b0 + (thr - b0) / 2))
        out[name] = res
    return {"mu0": mu0, "sd0": sd0, "n0": n0, "trades_per_year": trades_per_year, "signale": out}
