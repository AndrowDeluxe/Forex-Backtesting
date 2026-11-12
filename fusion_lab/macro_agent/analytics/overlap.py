"""Unabhaengigkeits-Pruefung der Gruende (Meridian "Attribution / Overlap", 12.11.2026).

Anlass: Die SMT-Gates zaehlten Momentum dreifach (Memory makro_gates_zaehlen_momentum_dreifach).
Statt Gruende zu zaehlen: Korrelation der Faktor-z-Werte (Monatsenden, ueber alle Waehrungen gepoolt) und
effektive Zahl unabhaengiger Gruende je Idee: N_eff = (Σc)² / (cᵀ R c) fuer die unterstuetzenden
Beitraege c (Faktor-Differenz in Ideenrichtung > 0). Zwei perfekt korrelierte Gruende zaehlen als einer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dollar_factor import n_eff


def factor_corr(sc: dict[str, pd.DataFrame], factors: list[str]) -> pd.DataFrame:
    """Korrelation der Faktor-z-Werte an Monatsenden, gestapelt ueber Waehrungen."""
    cols = {}
    for f in factors:
        z = sc[f]
        z = z.groupby(z.index.to_period("M")).tail(1)
        cols[f] = z.stack(future_stack=True)
    return pd.DataFrame(cols).corr()


def score_n_eff(corr: pd.DataFrame) -> float:
    c = corr.dropna(how="all").dropna(axis=1, how="all")
    return round(n_eff(c.fillna(0).values), 2) if len(c) else 0.0


def reasons(diffs: dict[str, float | None], side: str, corr: pd.DataFrame) -> dict:
    sign = 1.0 if side == "long" else -1.0
    support = {f: sign * v for f, v in diffs.items() if v is not None and sign * v > 0 and f in corr}
    if not support:
        return {"gruende": [], "anzahl": 0, "n_eff": 0.0}
    names = list(support)
    c = np.array([support[f] for f in names])
    r = corr.loc[names, names].fillna(0).to_numpy(copy=True)
    np.fill_diagonal(r, 1.0)
    ne = float(c.sum() ** 2 / (c @ r @ c))
    return {"gruende": names, "anzahl": len(names), "n_eff": round(ne, 2)}
