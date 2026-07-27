import numpy as np
import pandas as pd
import pytest

from strategy.indicators import (
    _wilder_smooth,
    compute_adx,
    compute_prev_session_extremes,
    compute_vwap_and_deviation,
)


def _bars(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="h", tz="UTC")
    df = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close", "volume"])
    return df


def test_vwap_matches_manual_calculation():
    df = _bars(
        [
            [1.0, 1.02, 0.98, 1.00, 100],
            [1.00, 1.06, 1.00, 1.05, 200],
            [1.05, 1.05, 1.01, 1.02, 100],
        ]
    )
    out = compute_vwap_and_deviation(df, reset_hour=0)

    typical = (df["high"] + df["low"] + df["close"]) / 3
    manual_vwap = (typical * df["volume"]).cumsum() / df["volume"].cumsum()

    assert np.allclose(out["vwap"].to_numpy(), manual_vwap.to_numpy())
    assert np.allclose(out["deviation"].to_numpy(), ((df["close"] - manual_vwap) / manual_vwap).to_numpy())


def test_vwap_resets_at_session_boundary():
    idx = pd.date_range("2024-01-01 20:00", periods=6, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 6, "high": [1.01] * 6, "low": [0.99] * 6,
            "close": [1.0, 1.02, 1.04, 2.0, 2.02, 2.04],
            "volume": [10] * 6,
        },
        index=idx,
    )
    out = compute_vwap_and_deviation(df, reset_hour=22)
    # bars at 20:00,21:00 -> session A; 22:00,23:00,00:00,01:00 -> session B
    assert out["session"].iloc[0] == out["session"].iloc[1]
    assert out["session"].iloc[1] != out["session"].iloc[2]
    # vwap must not carry session-A volume into session B: first bar of
    # session B (close=1.04) must equal its own typical price alone.
    assert out["vwap"].iloc[2] == pytest.approx((1.01 + 0.99 + 1.04) / 3)


def test_prev_session_extremes_has_no_lookahead_into_current_session():
    df = _bars(
        [
            [1.0, 1.10, 0.90, 1.00, 10],  # session 1 (day 1)
            [1.0, 1.05, 0.95, 1.00, 10],  # session 1
            [2.0, 2.50, 1.50, 2.00, 10],  # session 2 (day 2) - own extreme must not leak
            [2.0, 2.05, 1.95, 2.00, 10],  # session 2
        ]
    )
    idx = pd.DatetimeIndex(
        [pd.Timestamp("2024-01-01 01:00", tz="UTC"), pd.Timestamp("2024-01-01 02:00", tz="UTC"),
         pd.Timestamp("2024-01-02 01:00", tz="UTC"), pd.Timestamp("2024-01-02 02:00", tz="UTC")]
    )
    df.index = idx
    vwapped = compute_vwap_and_deviation(df, reset_hour=0)
    out = compute_prev_session_extremes(vwapped)

    assert out["prev_high"].iloc[0:2].isna().all()  # no prior session yet
    assert (out["prev_high"].iloc[2:4] == 1.10).all()
    assert (out["prev_low"].iloc[2:4] == 0.90).all()


def test_wilder_smooth_seed_is_mean_not_sum():
    # A constant-input series must produce a constant smoothed output.
    # The paper's Appendix A code seeds with sum(first n) instead of
    # mean(first n), which would blow this up to n times the true value.
    series = pd.Series([2.0] * 40)
    smoothed = _wilder_smooth(series, period=14)
    assert smoothed.iloc[14] == pytest.approx(2.0)
    assert smoothed.iloc[-1] == pytest.approx(2.0)


def test_adx_bounded_between_0_and_100():
    rng = np.random.default_rng(0)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = 1.0 + np.cumsum(rng.normal(0, 0.001, n))
    high = close + np.abs(rng.normal(0, 0.0005, n))
    low = close - np.abs(rng.normal(0, 0.0005, n))
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 100}, index=idx)
    out = compute_adx(df, n=14)
    valid = out["adx"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all()
