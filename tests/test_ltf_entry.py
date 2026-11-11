import numpy as np
import pandas as pd

from htf_daily_trade.ltf_entry import sim_one, trigger_events


def _bars(n: int = 600, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 1.10 + np.cumsum(rng.normal(0, 0.0008, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.0006, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.0006, n)
    idx = pd.date_range("2020-01-06", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c}, index=idx)


def _htf(d: pd.DataFrame) -> pd.DataFrame:
    return d.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


def test_trigger_kein_vorgriff():
    d = _bars()
    cut = 400
    full, _ = trigger_events(d, _htf(d))
    part, _ = trigger_events(d.iloc[:cut], _htf(d.iloc[:cut]))
    for key in ("L1", "L2", "L3"):
        for side in ("long", "short"):
            a = full[(key, side)]
            a = a[a[:, 0] < cut - 3] if len(a) else a       # Swings brauchen k=2 Kerzen Bestaetigung
            b = part[(key, side)]
            b = b[b[:, 0] < cut - 3] if len(b) else b
            assert np.allclose(a, b), (key, side)


def test_stop_vor_ziel_in_derselben_kerze():
    h = np.array([1.0, 1.2, 1.0])
    l = np.array([1.0, 0.8, 1.0])
    c = np.array([1.0, 1.0, 1.0])
    ex_i, ex_px = sim_one(h, l, c, 0, 1.0, 0.9, 1.1, 2, 1, False)
    assert ex_i == 1 and ex_px == 0.9


def test_limit_fuellkerze_nur_stop():
    h = np.array([1.2, 1.0, 1.25])
    l = np.array([0.95, 0.99, 1.0])
    c = np.array([1.0, 1.0, 1.2])
    ex_i, ex_px = sim_one(h, l, c, 0, 1.0, 0.9, 1.1, 2, 1, True)   # Ziel in der Fuellkerze zaehlt nicht
    assert ex_i == 2 and ex_px == 1.1
