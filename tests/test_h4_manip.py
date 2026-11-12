import numpy as np
import pandas as pd

from htf_daily_trade import h4_manip as hm


def _bars(rows):
    idx = pd.date_range("2020-01-06 00:00", periods=len(rows), freq="4h", tz="UTC")
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


def test_sweep_braucht_zwei_vorkerzen_und_schluss_zurueck():
    x = _bars([[1.0, 1.1, 0.9, 1.0], [1.0, 1.1, 0.95, 1.0],
               [1.0, 1.05, 0.85, 1.02],     # Tief unter beiden Vorkerzen, Schluss zurueck -> long
               [1.02, 1.04, 0.80, 0.82],    # Tief drunter, Schluss NICHT zurueck -> kein Signal
               [0.82, 0.9, 0.81, 0.85]])
    s = hm.manipulations(x)
    assert [(z["k"], z["side"]) for z in s] == [(2, "long")]
    assert s[0]["stop"] == 0.85


class _M(hm.Market):
    def __init__(self, x):  # nur Arrays, ohne Datenladen
        self.name, self.cost = "EURUSD", 0.0
        self.x = x
        self.o, self.h, self.l, self.c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        n = len(x)
        self.up_break = np.zeros(n, bool)
        self.dn_break = np.zeros(n, bool)
        self.sw_hi, self.sw_lo = [], []
        self.prev_day = np.full(n, -1)
        self.w_hi = self.w_lo = np.full(n, np.nan)


def test_e2_verfaellt_wenn_folgekerze_das_extrem_bricht(monkeypatch):
    monkeypatch.setattr(hm, "swap_r", lambda *a, **k: 0.0)
    x = _bars([[1.0, 1.1, 0.9, 1.0]] * 2 + [[1.0, 1.05, 0.85, 1.02], [1.02, 1.03, 0.84, 1.0], [1.0, 1.2, 0.99, 1.1]])
    m = _M(x)
    s = {"k": 2, "side": "long", "stop": 0.85, "wick": 0.8}
    assert m.trade(s, "E2", "TA", "B0", len(x) - 1) is None
    assert m.trade(s, "E1", "TA", "B0", len(x) - 1) is not None


def test_be_erst_nach_bestaetigtem_bruch(monkeypatch):
    monkeypatch.setattr(hm, "swap_r", lambda *a, **k: 0.0)
    rows = [[1.0, 1.1, 0.9, 1.0]] * 2 + [[1.0, 1.05, 0.85, 1.0],     # k=2 Manipulation, Stop 0.85
            [1.0, 1.08, 0.97, 1.07],                                  # k=3 Einstieg 1.0, Bruch (BOS) am Schluss
            [1.07, 1.08, 0.99, 1.0],                                  # k=4 unter Einstieg -> BE greift
            [1.0, 1.01, 0.84, 0.9]]
    x = _bars(rows)
    m = _M(x)
    m.up_break[3] = True
    s = {"k": 2, "side": "long", "stop": 0.85, "wick": 0.8}
    r_be = m.trade(s, "E1", "TA", "B1", len(x) - 1)
    r_no = m.trade(s, "E1", "TA", "B0", len(x) - 1)
    assert abs(r_be["r"]) < 1e-9 and r_be["exit_k"] == 4
    assert r_no["r"] < -0.99


def test_fractal_ziel_nutzt_nur_bekannte_und_unberuehrte_hochs():
    x = _bars([[1.0, 1.1, 0.9, 1.0]] * 10)
    m = _M(x)
    m.sw_hi = [(3, 1, 1.30), (6, 4, 1.20), (9, 7, 1.15)]   # (bestaetigt, Kerze, Preis)
    m.h = m.h.copy()
    assert m.target("TB", 1, 1.0, 0.05, known=6, live=7) == 1.20   # (9,7) erst spaeter bestaetigt -> unsichtbar
    m.h[5] = 1.21                                                  # 1.20 nach seiner Bildung abgeholt
    assert m.target("TB", 1, 1.0, 0.05, known=6, live=7) == 1.30
