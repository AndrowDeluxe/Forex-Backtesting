"""Tests fuer fusion_lab/g8 (Score-Definition, Gewichte, kein Lookahead)."""

import numpy as np
import pandas as pd

from fusion_lab.g8.backtest import daily_returns, weights
from fusion_lab.g8.model import score

CCY = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]


def _logv(n=200, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    lv = pd.DataFrame(rng.normal(0, 0.005, (n, 8)).cumsum(axis=0), index=idx, columns=CCY)
    lv["USD"] = 0.0
    return lv


def test_score_is_mean_of_horizons():
    sc, hs = score(_logv(), "xs")
    assert np.allclose(sc.iloc[-1], (hs["w1"].iloc[-1] + hs["m1"].iloc[-1] + hs["m3"].iloc[-1]) / 3)


def test_weights_balanced_and_k_legs():
    sc, _ = score(_logv(), "xs")
    w = weights(sc, 2, "daily").iloc[-1]
    assert np.isclose(w.sum(), 0) and (w > 0).sum() == 2 and (w < 0).sum() == 2
    assert np.isclose(w.abs().sum(), 1.0)
    assert w.idxmax() in sc.iloc[-1].nlargest(2).index


def test_no_lookahead_future_change_does_not_alter_past_returns():
    lv = _logv()
    r1 = daily_returns(lv, 2, "daily")
    lv2 = lv.copy()
    lv2.iloc[-1, 1:] += 0.5  # nur der letzte Tag aendert sich
    r2 = daily_returns(lv2, 2, "daily")
    assert np.allclose(r1.iloc[:-1], r2.iloc[:-1])
