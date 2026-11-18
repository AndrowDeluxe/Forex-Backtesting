"""Tests Gold-Richtungs-Komposition und Twist-Variante der Zinskurve (18.11.2026)."""

import pandas as pd

from fusion_lab.filters.gold_komposition import GoldRichtungKomposition, _vor, combine
from fusion_lab.filters.zinskurve_regime import confirmed

DAYS = pd.bdate_range("2026-01-05", periods=4)


def _votes(rows):
    return pd.DataFrame(rows, columns=["Z", "M", "R2", "RR", "C"], index=DAYS[: len(rows)])


def test_k1_mehrheit():
    v = _votes([[1, 1, 0, 0, 0], [1, -1, 0, 0, 0], [-1, -1, -1, 1, 0]])
    assert combine(v, "K1").tolist() == [1, 0, -1]


def test_k2_veto_durch_m_oder_z():
    v = _votes([[1, -1, 1, 1, 1], [-1, 1, 1, 1, 0], [0, 0, 1, 1, 0]])
    assert combine(v, "K2").tolist() == [0, 0, 1]


def test_k3_einstimmig_mindestens_drei():
    v = _votes([[1, 1, 1, 0, 0], [1, 1, 0, 0, 0], [1, 1, 1, -1, 0]])
    assert combine(v, "K3").tolist() == [1, 0, 0]


def test_vor_nutzt_nur_vortage():
    s = pd.Series([1.0, -1.0], index=pd.to_datetime(["2026-01-05", "2026-01-06"]))
    out = _vor(s, DAYS)
    assert pd.isna(out.iloc[0]) and out.iloc[1] == 1 and out.iloc[2] == -1


def test_twist_unterbricht_bestaetigung_nur_mit_reset():
    reg = pd.Series(["Goldilocks"] * 5 + ["Inflation", "Inflation", "Twist", "Inflation", "Inflation", "Inflation"],
                    index=pd.bdate_range("2026-01-05", periods=11))
    assert confirmed(reg, 5).iloc[-1] == "Goldilocks"
    assert confirmed(reg, 5, twist_resets=False).iloc[-1] == "Inflation"


def test_klasse_schnittstelle():
    v = _votes([[1, 1, 1, 0, 0], [-1, -1, -1, 0, 0]])
    k = GoldRichtungKomposition(rule="K1", frame=v)
    assert k.direction(DAYS[0]) == 1 and k.allows("long", DAYS[0]) and not k.allows("short", DAYS[0])
    assert k.direction(DAYS[1]) == -1 and k.explain(DAYS[1])["stimmen"]["M"] == -1
