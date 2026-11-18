"""Edelmetalle HTF: kein Vorgriff, Wochen-Bildung, Verfuegbarkeit je Quelle, Regime-Rendite, Kontrollen, Lock."""

import numpy as np
import pandas as pd
import pytest

from fusion_lab.metals_htf import backtest as B, features as F, spec as S
from research_lock import Lock


def test_weekly_takes_last_value_and_drops_stale():
    days = pd.bdate_range("2024-01-01", "2024-01-31")
    s = pd.Series(np.arange(len(days), dtype=float), index=days)
    s = s.drop(pd.Timestamp("2024-01-12"))                      # Freitag fehlt -> Donnerstag
    s = s[(s.index < "2024-01-15") | (s.index > "2024-01-26")]   # Woche 15.-26. leer
    grid = F.week_grid(pd.Timestamp("2024-01-26"), "2024-01-05")
    w = F.weekly(s, grid)
    assert w[pd.Timestamp("2024-01-05")] == 4.0
    assert w[pd.Timestamp("2024-01-12")] == 8.0                  # Do 11.01.
    assert np.isnan(w[pd.Timestamp("2024-01-26")])               # letzter Wert 12.01. -> zu alt


def test_fred_value_of_friday_not_visible_on_friday():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-04", "2024-01-05"]))   # Do, Fr
    w = F.weekly(F.lag_bdays(s), F.week_grid(pd.Timestamp("2024-01-12"), "2024-01-05"))
    assert w[pd.Timestamp("2024-01-05")] == 1.0 and w[pd.Timestamp("2024-01-12")] == 2.0


def test_cftc_report_available_on_friday_only():
    idx = pd.Series([0.7], index=pd.to_datetime(["2024-01-09"]))   # Dienstag
    a = F.avail_on(idx, pd.Series(idx.index + pd.Timedelta(days=3)))
    assert a.index[0] == pd.Timestamp("2024-01-12")
    days = pd.to_datetime(["2024-01-11", "2024-01-12"])
    w = F.weekly(a, pd.DatetimeIndex(days), max_age=10)
    assert np.isnan(w.iloc[0]) and w.iloc[1] == 0.7


def test_rolling_pct_has_no_lookahead():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(size=300))
    a = F.rolling_pct(x)
    y = x.copy()
    y.iloc[200:] = 99.0
    b = F.rolling_pct(y)
    pd.testing.assert_series_equal(a.iloc[:200], b.iloc[:200])
    assert a.iloc[:S.PCT_MIN - 1].isna().all() and a.iloc[S.PCT_MIN - 1:].between(0, 1).all()


def test_cot_index_range():
    net = pd.Series(np.r_[np.linspace(-100, 100, 40), 0.0])
    ci = F.cot_index(net)
    assert ci.iloc[-1] == pytest.approx(0.5) and ci.dropna().between(0, 1).all()


def test_positions_thirds():
    p = B.positions(pd.Series([0.9, 0.5, 0.1, np.nan]))
    assert list(p) == [1.0, 0.0, -1.0, 0.0]


def test_pnl_matches_hand_calc():
    idx = pd.date_range("2024-01-05", periods=4, freq="W-FRI")
    pos = pd.Series([1.0, 1.0, -1.0, 0.0], index=idx)
    r1 = pd.Series([0.02, -0.01, 0.03, 0.01], index=idx)
    got = B.pnl(pos, r1, cost_bps=10.0)
    exp = [0.02 - 0.001, -0.01, -0.03 - 2 * 0.001, 0.0 - 0.001]
    assert np.allclose(got.values, exp)
    assert np.allclose(B.pnl(pos, r1, 0.0, swap_pa=0.052).values, [0.019, -0.011, -0.031, 0.0])


def test_pnl_skips_missing_return_weeks():
    idx = pd.date_range("2024-01-05", periods=3, freq="W-FRI")
    got = B.pnl(pd.Series([1.0, 1.0, 1.0], index=idx), pd.Series([0.01, np.nan, 0.01], index=idx), 0.0)
    assert len(got) == 2


def test_random_timing_keeps_exposure():
    idx = pd.date_range("2010-01-01", periods=200, freq="W-FRI")
    r1 = pd.Series(np.random.default_rng(2).normal(0.002, 0.02, 200), index=idx)
    always = pd.Series(1.0, index=idx)
    sims = B.random_timing(always, r1, 0.0, n=20)
    assert np.allclose(sims, B.sharpe(B.pnl(always, r1, 0.0)))   # permutiertes "immer long" bleibt immer long


def test_ic_monotone_and_nw_t():
    x = pd.Series(np.arange(100.0))
    assert B.ic(x, x * 2, 1)["ic"] == pytest.approx(1.0, abs=1e-9)
    e = pd.Series(np.random.default_rng(3).normal(0.1, 1, 500))
    simple = e.mean() / e.std(ddof=0) * np.sqrt(len(e))
    assert B.nw_tstat(e, 0) == pytest.approx(simple, rel=1e-9)


def test_spec_preregistration_consistent():
    assert len(S.LOOKBACKS) <= 9 and set(S.COST_BPS) == set(S.METALS)
    assert S.FEATURES["cot_mit"]["vorz"]["GOLD"] == -S.FEATURES["cot_contra"]["vorz"]["GOLD"]
    names = [S.name(f, L) for f, L in S.variants()]
    assert len(names) == len(set(names))


def test_lock_split_slices(tmp_path):
    lk = Lock("t_metals", lock_dir=tmp_path)
    lk.register_split(*S.SPLIT)
    idx = pd.date_range("2016-12-30", "2018-01-12", freq="W-FRI")
    s = pd.Series(1.0, index=idx)
    assert lk.is_only(s).index.max() <= pd.Timestamp("2017-12-31")
    assert lk.oos_only(s).index.min() >= pd.Timestamp("2018-01-01")
