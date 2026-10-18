"""G8-Waehrungsstaerke: Nachbau des SMH-Querschnittsmodells (Phase 1, Schritt 4).

Bekannt aus dem Original (Fusszeile/Legende der Tagesbilder):
  SCORE = Abweichung vom Durchschnitt der acht, ueber +1 auffaellig stark;
  1W/1M/3M = derselbe Wert ueber Woche, Monat, Quartal; nachgerechnet am
  06.10.2026: SCORE = Mittel(1W, 1M, 3M).
Unbekannt und per calibrate.py gegen die veroeffentlichten Tabellen bestimmt:
wie die Horizont-Werte normiert sind (NORMS). Ergebnis 2026-10-10 (23 Tabellen,
24.08.-06.10.): "xs" mit FRED, Stichtag selbst -- Score-Korrelation 0,98, Rang-
Korrelation je Tag 0,95, mittlere Abweichung 0,12. DEFAULT_NORM = "xs".

Horizonte in Handelstagen: 1W = 5, 1M = 21, 3M = 63.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = {"w1": 5, "m1": 21, "m3": 63}
DEFAULT_NORM = "xs"
NORMS = ("xs", "ts_expanding", "ts_rolling1y", "pool_expanding")


def relative_returns(logv: pd.DataFrame, h: int) -> pd.DataFrame:
    """h-Tage-Logrendite jeder Waehrung (in USD) minus Mittel der acht."""
    r = logv.diff(h)
    return r.sub(r.mean(axis=1), axis=0)


def normalize(rel: pd.DataFrame, norm: str, h: int) -> pd.DataFrame:
    if norm == "xs":  # Querschnitts-z am selben Tag (kalibriert 10.10.: beste Passung, ddof=1)
        return rel.div(rel.std(axis=1, ddof=1), axis=0)
    if norm == "ts_expanding":  # gegen die eigene Historie der Waehrung
        return rel / rel.expanding(min_periods=252).std()
    if norm == "ts_rolling1y":
        return rel / rel.rolling(252, min_periods=126).std()
    if norm == "pool_expanding":  # eine gemeinsame Skala fuer alle acht
        sq = (rel ** 2).mean(axis=1).expanding(min_periods=252).mean()
        return rel.div(np.sqrt(sq), axis=0)
    raise ValueError(norm)


def horizon_scores(logv: pd.DataFrame, norm: str) -> dict[str, pd.DataFrame]:
    return {k: normalize(relative_returns(logv, h), norm, h) for k, h in HORIZONS.items()}


def score(logv: pd.DataFrame, norm: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    hs = horizon_scores(logv, norm)
    return (hs["w1"] + hs["m1"] + hs["m3"]) / 3.0, hs


def ranking(score_row: pd.Series) -> pd.Series:
    return score_row.sort_values(ascending=False)
