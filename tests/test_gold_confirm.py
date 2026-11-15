"""Gold Confirmation Score: kein Vorgriff, Wertebereich, Gewichte (fusion_lab/gold_confirm)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fusion_lab.gold_confirm import components as comp
from fusion_lab.gold_confirm import data as gdata
from fusion_lab.gold_confirm.score import WEIGHTS, blocks, score

pytestmark = pytest.mark.skipif(not (gdata.DATA_DIR / "spot.parquet").exists(),
                                reason="Rohdaten fehlen: python -m fusion_lab.gold_confirm.data")

CUTOFF = pd.Timestamp("2018-06-15")


def _truncated_loader(cutoff: pd.Timestamp):
    real = gdata.load

    def load(name: str) -> pd.DataFrame:
        d = real(name)
        if name == "cftc":
            return d[d["report"] <= cutoff]
        if name == "imf":
            return d[d["month"] <= cutoff]
        return d[d.index <= cutoff]
    return load


def test_no_lookahead(monkeypatch):
    full = comp.components()
    monkeypatch.setattr(comp, "load", _truncated_loader(CUTOFF))
    cut = comp.components()
    common = cut.index[cut.index <= CUTOFF]
    a, b = full.loc[common], cut.loc[common]
    diff = (a - b).abs().max()
    assert diff.max() < 1e-9, f"Vorgriff in: {diff[diff >= 1e-9].to_dict()}"


def test_range_and_score():
    c = comp.components()
    assert ((c.min() >= 0) & (c.max() <= 1)).all()
    s = score(blocks(c))
    assert s.dropna().between(0, 100).all()


def test_weights_renormalize_when_block_missing():
    idx = pd.date_range("2020-01-01", periods=3)
    bl = pd.DataFrame({"FLOW": [1.0, 1.0, 1.0], "PHYSICAL": [np.nan, 0.0, np.nan],
                       "PRICE": [1.0, 1.0, np.nan], "MACRO": [1.0, 1.0, np.nan]}, index=idx)
    s = score(bl)
    assert s.iloc[0] == pytest.approx(100.0)            # Physical fehlt -> uebrige 75 % auf 100 % skaliert
    assert s.iloc[1] == pytest.approx(100 * (1 - WEIGHTS["PHYSICAL"]))
    assert np.isnan(s.iloc[2])                            # nur 40 % Gewicht verfuegbar -> kein Score


def test_macro_veto_filter_sides():
    from fusion_lab.filters.gold_macro_veto import GoldMacroVetoFilter
    idx = pd.date_range("2024-01-01", periods=3)
    f = pd.DataFrame({"MACRO": [0.80, 0.20, 0.50], "score": [50, 50, 50]}, index=idx)
    v = GoldMacroVetoFilter(frame=f)
    # Wert vom Vortag: 02.01. sieht 80 -> kein Short; 03.01. sieht 20 -> kein Long; 04.01. sieht 50 -> alles
    assert v.allows("long", "2024-01-02") and not v.allows("short", "2024-01-02")
    assert not v.allows(1, "2024-01-03") and v.allows(-1, "2024-01-03")
    assert v.allows("long", "2024-01-04") and v.allows("short", "2024-01-04")
    assert v.explain("2024-01-03")["MACRO"] == 20.0     # Vortag 02.01.
