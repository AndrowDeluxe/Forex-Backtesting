import numpy as np
import pandas as pd

from htf_daily_trade import h4_v4 as v4


def test_feiertage_und_weihnachten():
    b = v4.blocked_days("2020-01-01", "2021-01-01")
    assert pd.Timestamp("2020-09-07") in b            # Labor Day
    assert pd.Timestamp("2020-09-04") in b            # Vortag (Freitag)
    assert pd.Timestamp("2020-05-25") in b            # UK Spring Bank / Memorial Day
    assert pd.Timestamp("2020-04-10") in b            # Karfreitag
    assert pd.Timestamp("2020-09-08") not in b
    assert v4.christmas(pd.Timestamp("2020-12-23")) and v4.christmas(pd.Timestamp("2021-01-05"))
    assert not v4.christmas(pd.Timestamp("2020-12-10"))


class _M:
    def __init__(self, rows):
        idx = pd.date_range("2020-01-06", periods=len(rows), freq="4h", tz="UTC")
        self.x = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)
        self.o, self.h, self.l, self.c = (self.x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        self.name = "EURUSD"


def test_teilgewinn_50_bei_1r_dann_be(monkeypatch):
    monkeypatch.setattr(v4, "swap_r", lambda *a, **k: 0.0)
    # Einstieg 1.0, Stop 0.9 -> 1R = 1.1; erreicht 1.1, faellt dann auf 1.0 (BE)
    m = _M([[1.0, 1.0, 0.95, 1.0], [1.0, 1.12, 0.98, 1.05], [1.05, 1.06, 0.99, 1.0], [1.0, 1.0, 0.9, 0.9]])
    g, r, j = v4.simulate(m, 0, 1, 0.9, ("R3", 1.0, 0.5, None, 60), 3, 0.0)
    assert abs(g - 0.5) < 1e-9 and j == 2


def test_zeit_be_schliesst_ohne_1r(monkeypatch):
    monkeypatch.setattr(v4, "swap_r", lambda *a, **k: 0.0)
    m = _M([[1.0, 1.0, 0.95, 1.0]] + [[1.0, 1.02, 0.97, 0.99]] * 5)
    g, r, j = v4.simulate(m, 0, 1, 0.9, ("R3", None, 0.0, 3, 60), 5, 0.0)
    assert j == 3 and abs(g - (-0.1)) < 1e-9          # nach 3 Kerzen ohne 1R im Minus geschlossen
