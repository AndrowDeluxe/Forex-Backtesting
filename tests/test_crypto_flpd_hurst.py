import numpy as np
import pandas as pd

from crypto_flpd.hurst import dfa_hurst, hurst_collapse_signal, rolling_hurst


def test_dfa_hurst_white_noise_is_near_half():
    rng = np.random.default_rng(0)
    x = rng.normal(size=20_000)
    h = dfa_hurst(x)
    assert 0.40 < h < 0.60


def test_dfa_hurst_persistent_series_exceeds_half():
    # AR(1) with a strong positive coefficient gives genuinely positively-
    # autocorrelated increments (each step biased to continue the prior
    # step's direction) - a coarse but standard directional sanity check
    # (not a precision claim) that DFA responds correctly to persistence:
    # clearly above the H=0.5 white-noise baseline from the test above.
    rng = np.random.default_rng(1)
    n = 20_000
    phi = 0.5
    eps = rng.normal(size=n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    h = dfa_hurst(x)
    assert h > 0.55


def test_dfa_hurst_too_short_returns_nan():
    assert np.isnan(dfa_hurst(np.random.default_rng(2).normal(size=50)))


def test_rolling_hurst_is_causal_and_forward_filled():
    rng = np.random.default_rng(3)
    idx = pd.date_range("2024-01-01", periods=3000, freq="h", tz="UTC")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(scale=0.001, size=3000))), index=idx)

    ht = rolling_hurst(close, window=500, step=50)

    assert ht.iloc[:499].isna().all()
    assert ht.iloc[500:].notna().any()
    # Truncating the tail must not change any earlier value - a value at
    # bar t must never depend on bars after t.
    ht_truncated = rolling_hurst(close.iloc[:2000], window=500, step=50)
    common = ht.iloc[:2000].dropna().index.intersection(ht_truncated.dropna().index)
    assert len(common) > 0
    assert np.allclose(ht.loc[common], ht_truncated.loc[common])


def test_hurst_collapse_signal_flags_an_engineered_drop():
    idx = pd.date_range("2024-01-01", periods=200, freq="D", tz="UTC")
    values = np.concatenate([np.full(100, 0.65), np.full(100, 0.40)])
    ht = pd.Series(values, index=idx)
    collapse = hurst_collapse_signal(ht, z_window=20, z_thresh=2.0)
    assert collapse.iloc[100]  # the single bar where H drops from 0.65 to 0.40
    assert not collapse.iloc[:99].any()
    assert not collapse.iloc[105:].any()
