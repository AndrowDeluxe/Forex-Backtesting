"""Gold-Lagebild "wer kauft Gold" fuer das Makro-Fact-Sheet (Kontext, KEIN Signal).

Alle Reihen frei: GLD-Bestand (SPDR), Shanghai-Praemie (SGE-PM vs. XAUUSD), Zentralbanken (IMF IRFCL,
nur gemeldete Kaeufe), dazu der MACRO-Block. Nur Daten mit Stand vor `day`.
Daten aktualisieren: python -m fusion_lab.gold_confirm.data
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.gold_confirm.components import raw_components
from fusion_lab.gold_confirm.data import load
from fusion_lab.gold_confirm.score import build

T_PER_MOZ = 31.1035  # 1 Mio. Feinunzen = 31,1 t


def gold_context(day=None) -> dict:
    day = pd.Timestamp(day or pd.Timestamp.now()).normalize()
    cut = day - pd.Timedelta(days=1)
    gld = load("gld")["tonnes"].loc[:cut].dropna()
    raw = raw_components().loc[:cut]
    f = build().loc[:cut]
    last = lambda s: s.dropna().iloc[-1] if s.notna().any() else float("nan")  # noqa: E731
    return {
        "stand": cut.date().isoformat(),
        "gld_tonnen": round(float(gld.iloc[-1]), 1),
        "gld_5T_t": round(float(gld.iloc[-1] - gld.iloc[-6]), 1),
        "gld_20T_t": round(float(gld.iloc[-1] - gld.iloc[-21]), 1),
        "china_praemie_%": round(float(last(raw["p_china"])) * 100, 2),
        "zentralbanken_12M_t": round(float(last(raw["p_cb"])) * T_PER_MOZ, 0),
        "macro_block": round(float(last(f["MACRO"])) * 100, 1),
        "macro_stand": f["MACRO"].dropna().index[-1].date().isoformat(),
    }


if __name__ == "__main__":
    print(gold_context())
