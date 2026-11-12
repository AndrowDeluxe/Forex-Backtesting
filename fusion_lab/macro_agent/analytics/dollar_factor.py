"""Dollar-Faktor (Meridian-Baustein, 12.11.2026): einmal gerechnet, von allen Paaren gemeinsam genutzt.

USD-Faktor = mittlere Tagesrendite des Dollars gegen die 7 anderen Waehrungen (USD-Seite: EURUSD negativ,
USDJPY positiv). Je Markt: Beta zum Faktor und Anteil der Schwankung, den der Dollar erklaert (R²).
Fuer eine Ideenliste: Dollar-Anteil je Idee und effektive Zahl unabhaengiger Wetten
(N_eff = (Σλ)² / Σλ² ueber die Eigenwerte der Korrelation der Ideen-Renditen) -> "3 Ideen = 1 Dollar-Wette".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .markets import USD_PAIRS

WINDOW = 60


def _ret(prices: dict[str, pd.DataFrame], m: str) -> pd.Series:
    return np.log(prices[m]["Close"]).diff()


def usd_factor(prices: dict[str, pd.DataFrame]) -> pd.Series:
    side = {p: (1.0 if p.startswith("USD") else -1.0) * _ret(prices, p) for p in USD_PAIRS if p in prices}
    return pd.DataFrame(side).mean(axis=1, skipna=True).dropna()


def decompose(prices: dict[str, pd.DataFrame], factor: pd.Series, window: int = WINDOW) -> dict[str, dict]:
    out = {}
    f = factor.iloc[-window:]
    for m in prices:
        r = _ret(prices, m).reindex(f.index)
        d = pd.concat([r, f], axis=1).dropna()
        if len(d) < window // 2:
            out[m] = None
            continue
        beta = float(np.cov(d.iloc[:, 0], d.iloc[:, 1])[0, 1] / d.iloc[:, 1].var())
        r2 = float(d.corr().iloc[0, 1] ** 2)
        out[m] = {"beta": round(beta, 2), "dollar_anteil_pct": round(100 * r2, 0)}
    return out


def n_eff(corr: np.ndarray) -> float:
    lam = np.clip(np.linalg.eigvalsh(corr), 0, None)
    return float(lam.sum() ** 2 / (lam ** 2).sum()) if lam.sum() > 0 else 0.0


def idea_bundle(prices: dict[str, pd.DataFrame], idea_list: list[dict], decomp: dict, window: int = WINDOW) -> dict:
    if not idea_list:
        return {"ideen": 0, "n_eff": None, "dollar_netto": 0.0, "text": "keine Ideen"}
    rets = {}
    usd = 0.0
    for i in idea_list:
        sign = 1.0 if i["seite"] == "long" else -1.0
        rets[i["markt"]] = sign * _ret(prices, i["markt"])
        beta = (decomp.get(i["markt"]) or {}).get("beta") or 0.0
        usd += sign * beta
    frame = pd.DataFrame(rets).iloc[-window:].dropna()
    ne = n_eff(frame.corr().values) if len(idea_list) > 1 and len(frame) > 10 else float(len(idea_list))
    txt = (f"{len(idea_list)} Ideen = {ne:.1f} unabhängige Wetten; Dollar-Netto {usd:+.1f} Einheiten"
           + (" (praktisch eine Dollar-Wette)" if ne < 1.5 and abs(usd) >= 0.7 * len(idea_list) else ""))
    return {"ideen": len(idea_list), "n_eff": round(ne, 2), "dollar_netto": round(usd, 2), "text": txt}
