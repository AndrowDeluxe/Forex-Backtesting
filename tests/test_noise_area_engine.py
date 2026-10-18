"""Tests fuer noise_area_momentum/engine.py: run_general muss die Paper-Logik von run() exakt treffen."""

import numpy as np
import pandas as pd

from noise_area_momentum.engine import N_BARS, run, run_general


def _grid(n_days=120, seed=3):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.0008, (n_days, N_BARS)), axis=1)
                         * (1 + 0.2 * rng.standard_normal((n_days, 1))))
    close *= np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))[:, None]
    open_ = np.column_stack([close[:, :1] * (1 + rng.normal(0, 0.003, (n_days, 1))), close[:, :-1]])
    high = np.maximum(open_, close) * 1.0002
    low = np.minimum(open_, close) * 0.9998
    return {"dates": pd.bdate_range("2024-01-01", periods=n_days), "open": open_, "high": high,
            "low": low, "close": close, "volume": rng.uniform(0.1, 1.0, (n_days, N_BARS))}


def test_paper_vwap_identisch():
    g = _grid()
    a = run(g, stop="vwap", cost_rt_bps=1.5)
    b = run_general(g, direction="mom", exit="vwap", cost_rt_bps=1.5)
    pd.testing.assert_series_equal(a["ret_net"], b["ret_net"])
    assert (a["trades"] == b["trades"]).all()


def test_gegenband_identisch():
    g = _grid(seed=5)
    a = run(g, stop="opp", vm=1.25, lookback=10)
    b = run_general(g, direction="mom", exit="opp", vm=1.25, lookback=10)
    pd.testing.assert_series_equal(a["ret_net"], b["ret_net"])


def test_gate_sperrt_tage_ohne_sie_zu_streichen():
    g = _grid(seed=7)
    gate = np.zeros(len(g["dates"]), dtype=bool)
    b = run_general(g, gate=gate)
    assert b["valid"].sum() > 0 and (b["ret_net"] == 0).all()
