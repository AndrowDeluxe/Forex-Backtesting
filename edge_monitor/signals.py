"""Badness-Statistiken auf einer Trade-Reihe.

Jede Funktion bekommt die R-Werte in zeitlicher Reihenfolge und die
Referenz "Edge intakt" (mu0, sd0 aus dem Kalibrierfenster) und liefert je
Trade k den Wert NACH Trade k. Hoeher = schlechter. Der Kill-Switch liest
fuer eine Entscheidung nur Werte von Trades, die zu diesem Zeitpunkt schon
geschlossen sind (siehe switch.py) -- hier gibt es deshalb keinen Zeitbezug.
"""
from __future__ import annotations

import numpy as np

ROLL_N = 30          # rollender Mittelwert
BAYES_W = 60         # Fenster fuer die Bayes-Likelihood
SIGNALS = ("roll_mean", "cusum", "sprt", "bayes", "drawdown")


def roll_mean(r: np.ndarray, mu0: float, sd0: float, n: int = ROLL_N) -> np.ndarray:
    """Abstand des Mittels der letzten n Trades unter mu0, in Standardfehlern."""
    c = np.cumsum(np.r_[0.0, r])
    out = np.full(len(r), np.nan)
    k = np.arange(len(r))
    ok = k + 1 >= n
    m = (c[k[ok] + 1] - c[k[ok] + 1 - n]) / n
    out[ok] = (mu0 - m) / (sd0 / np.sqrt(n))
    return out


def cusum(r: np.ndarray, mu0: float, sd0: float) -> np.ndarray:
    """Page-CUSUM auf Absinken von mu0 Richtung 0 (Referenz k = halber Abstand)."""
    z = (mu0 - r) / sd0
    kref = mu0 / sd0 / 2
    s, out = 0.0, np.empty(len(r))
    for i, v in enumerate(z):
        s = max(0.0, s + v - kref)
        out[i] = s
    return out


def sprt(r: np.ndarray, mu0: float, sd0: float) -> np.ndarray:
    """Wiederholter Wald-Test H1 mu=0 gegen H0 mu=mu0 (Normalannahme).
    Log-Likelihood-Quotient, nach unten bei 0 gekappt (wie CUSUM-Form)."""
    llr_step = ((r - mu0) ** 2 - r ** 2) / (2 * sd0 ** 2)
    s, out = 0.0, np.empty(len(r))
    for i, v in enumerate(llr_step):
        s = max(0.0, s + v)
        out[i] = s
    return out


def bayes(r: np.ndarray, mu0: float, sd0: float, n0: int, w: int = BAYES_W) -> np.ndarray:
    """P(mu < 0) aus Prior N(mu0, sd0^2/n0') und den letzten w Trades.
    Der Prior zaehlt hoechstens so viel wie w Trades, damit er neue Daten
    nicht erschlaegt. Rueckgabe als Wahrscheinlichkeit (hoeher = schlechter)."""
    from math import erf, sqrt
    n_prior = min(n0, w)
    c = np.cumsum(np.r_[0.0, r])
    out = np.empty(len(r))
    for i in range(len(r)):
        lo = max(0, i + 1 - w)
        n = i + 1 - lo
        s = c[i + 1] - c[lo]
        post_n = n_prior + n
        post_mu = (n_prior * mu0 + s) / post_n
        post_sd = sd0 / sqrt(post_n)
        out[i] = 0.5 * (1 + erf((0 - post_mu) / (post_sd * sqrt(2))))
    return out


def drawdown(r: np.ndarray, mu0: float, sd0: float) -> np.ndarray:
    """Aktueller Drawdown in R vom bisherigen Hoch (positiv = tiefer)."""
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    return peak - eq


def compute(name: str, r: np.ndarray, mu0: float, sd0: float, n0: int) -> np.ndarray:
    if name == "bayes":
        return bayes(r, mu0, sd0, n0)
    return {"roll_mean": roll_mean, "cusum": cusum, "sprt": sprt, "drawdown": drawdown}[name](r, mu0, sd0)
