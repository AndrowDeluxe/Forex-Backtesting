import numpy as np
import pandas as pd
import pytest

from checklist_strategy.indicators import (
    compute_regime_ok,
    nadaraya_watson_envelope,
    rsi,
    rsi_multi_length,
    rsi_with_ma,
)


def _price_series(n=200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.Series(100 + np.cumsum(rng.normal(0, 0.05, n)), index=idx)


def test_nw_envelope_is_causal_no_lookahead():
    close = _price_series(300)
    short = nadaraya_watson_envelope(close.iloc[:150], h=8, mult=3)
    long = nadaraya_watson_envelope(close, h=8, mult=3)
    # The value at bar 149 must be identical whether or not bars 150+ exist.
    assert short["mid"].iloc[-1] == pytest.approx(long["mid"].iloc[149], rel=1e-9)
    assert short["upper"].iloc[-1] == pytest.approx(long["upper"].iloc[149], rel=1e-9)


def test_nw_envelope_upper_above_lower():
    close = _price_series(300)
    env = nadaraya_watson_envelope(close, h=8, mult=3)
    valid = env.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["lower"] <= valid["mid"]).all()


def test_rsi_saturates_high_on_monotonic_uptrend():
    idx = pd.date_range("2024-01-01", periods=40, freq="15min", tz="UTC")
    close = pd.Series(np.linspace(1.0, 2.0, 40), index=idx)  # strictly rising, no losses at all
    r = rsi(close, length=14)
    assert r.dropna().iloc[-1] == pytest.approx(100.0)


def test_rsi_multi_length_matches_manual_average():
    close = _price_series(100)
    combined = rsi_multi_length(close, min_length=10, max_length=12)
    manual = pd.concat([rsi(close, 10), rsi(close, 11), rsi(close, 12)], axis=1).mean(axis=1)
    pd.testing.assert_series_equal(combined, manual, check_names=False)


def test_rsi_with_ma_returns_both_columns():
    close = _price_series(100)
    out = rsi_with_ma(close, rsi_length=14, ma_length=14)
    assert list(out.columns) == ["rsi", "rsi_ma"]
    assert out["rsi_ma"].dropna().shape[0] > 0


def test_regime_ok_is_false_through_a_clean_sustained_uptrend():
    idx = pd.date_range("2024-01-01", periods=400, freq="15min", tz="UTC")
    close = pd.Series(np.linspace(1.00, 1.20, 400), index=idx)
    df = pd.DataFrame({"open": close, "high": close + 0.0005, "low": close - 0.0005, "close": close}, index=idx)
    reg = compute_regime_ok(df)
    assert reg.dtype == bool
    assert not reg.isna().any()
    # A strong, clean, one-directional move should read as "trending" (ADX
    # high), so the "not strongly trending" half of the filter excludes it.
    assert reg.tail(100).mean() < 0.05


def test_regime_ok_lets_some_choppy_volatile_bars_through():
    idx = pd.date_range("2024-01-01", periods=400, freq="15min", tz="UTC")
    rng = np.random.default_rng(0)
    t = np.arange(400)
    close = pd.Series(1.10 + 0.01 * np.sin(t / 8) + rng.normal(0, 0.002, 400), index=idx)
    df = pd.DataFrame({"open": close, "high": close + 0.0015, "low": close - 0.0015, "close": close}, index=idx)
    reg = compute_regime_ok(df)
    # No sustained direction (low ADX) with real range (elevated ATR) should
    # pass at a materially higher rate than the clean-uptrend case above.
    assert reg.tail(150).mean() > 0.2
