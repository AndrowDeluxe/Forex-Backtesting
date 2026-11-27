"""M15-Einstieg CHoCH + 2 BOS (daily_neu_is.bos2_setup) auf einer kuenstlichen Zickzack-Reihe."""
import numpy as np
import pandas as pd

from htf_daily_trade.daily_neu_is import bos2_setup, struct_events


def zigzag(pivots, per_leg=4):
    px = [pivots[0]]
    for a, b in zip(pivots[:-1], pivots[1:]):
        px += list(np.linspace(a, b, per_leg + 1)[1:])
    c = np.array(px, dtype=float)
    idx = pd.date_range("2020-01-06", periods=len(c), freq="15min")
    return pd.DataFrame({"Open": c, "High": c + 0.01, "Low": c - 0.01, "Close": c}, index=idx)


def test_short_choch_bos1_bos2_limit_am_letzten_hoch():
    # Aufwaerts 110/105/112, dann CHoCH unter 105, LH 108, BOS1 unter 104, LH 106, BOS2 unter 101
    d = zigzag([100, 110, 105, 112, 104, 108, 101, 106, 98, 99])
    ev = struct_events(d)
    h, l, c = d["High"].to_numpy(), d["Low"].to_numpy(), d["Close"].to_numpy()
    res = bos2_setup(ev, h, l, c, 0, len(d), -1)
    assert res is not None
    b, lim, ext = res
    assert c[b] < 101 - 0.01                 # BOS2 = Bruch des Tiefs 101
    assert abs(lim - 106.01) < 1e-9          # Limit am Hoch, aus dem der BOS2-Schenkel startete
    assert abs(ext - 112.01) < 1e-9          # SA = Umkehr-Hoch
    assert c[b - 1] >= 101 - 0.01            # erste Kerze unter dem Tief -> kein Vorgriff


def test_kein_setup_ohne_zweiten_bos():
    d = zigzag([100, 110, 105, 112, 104, 108, 101, 106, 103])
    ev = struct_events(d)
    h, l, c = d["High"].to_numpy(), d["Low"].to_numpy(), d["Close"].to_numpy()
    assert bos2_setup(ev, h, l, c, 0, len(d), -1) is None


def test_long_gespiegelt():
    d = zigzag([200 - p for p in (100, 110, 105, 112, 104, 108, 101, 106, 98, 99)])
    ev = struct_events(d)
    h, l, c = d["High"].to_numpy(), d["Low"].to_numpy(), d["Close"].to_numpy()
    b, lim, ext = bos2_setup(ev, h, l, c, 0, len(d), 1)
    assert abs(lim - (94 - 0.01)) < 1e-9 and abs(ext - (88 - 0.01)) < 1e-9
