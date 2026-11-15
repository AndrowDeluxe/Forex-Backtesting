"""Gold Confirmation Score 0..100 aus den Bausteinen (components.py).

Bloecke wie im PDF: FLOW 40 %, PHYSICAL 25 %, PRICE RESPONSE 20 %, MACRO 15 %. Blockwert = Mittel der
verfuegbaren Bausteine. Fehlt ein ganzer Block (z. B. vor 2016 nur Zentralbanken im Physical-Block),
werden die Gewichte der uebrigen Bloecke anteilig hochskaliert.

    from fusion_lab.gold_confirm.score import GoldScoreFilter
    f = GoldScoreFilter(long_min=65, short_max=35)
    f.direction(day)        # +1 / -1 / 0, Score vom letzten Handelstag VOR `day`
    f.allows(side, day)     # side +1/-1; True, wenn der Score nicht dagegen steht (Veto-Logik)
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.gold_confirm.components import CATALOG, components

WEIGHTS = {"FLOW": 0.40, "PHYSICAL": 0.25, "PRICE": 0.20, "MACRO": 0.15}


def blocks(comp: pd.DataFrame, include: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Blockwerte 0..1. `include` kann je Block die Bausteine einschraenken (Varianten)."""
    out = {}
    for b in WEIGHTS:
        cols = include[b] if include and b in include else [k for k, v in CATALOG.items() if v[0] == b]
        cols = [c for c in cols if c in comp]
        out[b] = comp[cols].mean(axis=1, skipna=True) if cols else pd.Series(float("nan"), index=comp.index)
    return pd.DataFrame(out)


def score(bl: pd.DataFrame, weights: dict[str, float] = WEIGHTS) -> pd.Series:
    w = pd.DataFrame({b: bl[b].notna() * weights[b] for b in weights})
    total = w.sum(axis=1)
    s = sum(bl[b].fillna(0) * weights[b] for b in weights) / total
    return (100 * s).where(total >= 0.5)  # weniger als die Haelfte des Gewichts verfuegbar -> kein Score


_CACHE: dict[str, pd.DataFrame] = {}


def build(market: str = "GOLD") -> pd.DataFrame:
    """Bausteine + Bloecke + Score in einem Frame (Index: Handelstage XAUUSD)."""
    if market not in _CACHE:
        comp = components(market)
        bl = blocks(comp)
        _CACHE[market] = pd.concat([comp, bl, score(bl).rename("score")], axis=1)
    return _CACHE[market]


class GoldScoreFilter:
    """Schnittstelle wie GoldZinskurvenFilter/CotFlowFilter. Nutzt den Wert vom letzten Handelstag
    vor `day` (Score am Tagesende t -> Entscheidung am Tag t+1)."""

    def __init__(self, long_min: float = 65, short_max: float = 35, column: str = "score",
                 frame: pd.DataFrame | None = None):
        f = build() if frame is None else frame
        self.s = f[column] * (100 if column != "score" else 1)  # Bausteine/Bloecke liegen in 0..1
        self.long_min, self.short_max = long_min, short_max

    def value(self, day) -> float:
        day = pd.Timestamp(day).tz_localize(None).normalize() if pd.Timestamp(day).tzinfo else pd.Timestamp(day).normalize()
        prior = self.s.loc[:day - pd.Timedelta(days=1)].dropna()
        return float(prior.iloc[-1]) if len(prior) else float("nan")

    def direction(self, day) -> int:
        v = self.value(day)
        if v != v:
            return 0
        return 1 if v >= self.long_min else -1 if v <= self.short_max else 0

    def allows(self, side: int, day) -> bool:
        """Veto: long verboten, wenn Score <= short_max; short verboten, wenn Score >= long_min."""
        d = self.direction(day)
        return not (d != 0 and d == -side)
