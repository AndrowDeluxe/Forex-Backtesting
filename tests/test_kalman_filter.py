import numpy as np
import pandas as pd
import pytest

from strategy.kalman_filter import (
    add_kalman_deviation,
    estimate_kalman_params,
    kalman_smooth,
    rolling_zscore,
)


def test_kalman_smooth_constant_series_stays_constant():
    series = pd.Series([2.0] * 50)
    smoothed = kalman_smooth(series)
    assert smoothed.iloc[0] == pytest.approx(2.0)
    assert smoothed.iloc[-1] == pytest.approx(2.0)


def test_kalman_smooth_reduces_variance_of_noisy_series():
    rng = np.random.default_rng(0)
    n = 500
    true_trend = np.cumsum(rng.normal(0, 0.001, n))
    noisy = true_trend + rng.normal(0, 0.02, n)
    series = pd.Series(noisy)

    smoothed = kalman_smooth(series, measurement_noise_fraction=0.9)

    # denoised series must track the underlying trend more closely than the
    # raw noisy input does (lower error vs. the true, noise-free trend)
    raw_error = np.mean((noisy - true_trend) ** 2)
    smoothed_error = np.mean((smoothed.to_numpy() - true_trend) ** 2)
    assert smoothed_error < raw_error


def test_kalman_smooth_is_causal_no_lookahead():
    rng = np.random.default_rng(1)
    series = pd.Series(rng.normal(0, 1, 100).cumsum())

    full = kalman_smooth(series, process_var=0.01, measurement_var=0.05)
    truncated = kalman_smooth(series.iloc[:60], process_var=0.01, measurement_var=0.05)

    # value at bar 59 must be identical whether or not bars 60+ exist --
    # anything else would mean the filter is peeking into the future
    assert full.iloc[59] == pytest.approx(truncated.iloc[59])


def test_kalman_smooth_handles_nan_gaps():
    series = pd.Series([1.0, 1.1, np.nan, 1.2, 1.3])
    smoothed = kalman_smooth(series, process_var=0.001, measurement_var=0.01)
    assert not smoothed.isna().any()
    # carries the last estimate forward across the gap rather than resetting
    assert smoothed.iloc[2] == pytest.approx(smoothed.iloc[1])


def test_estimate_kalman_params_rejects_invalid_fraction():
    with pytest.raises(ValueError):
        estimate_kalman_params(pd.Series([1.0, 2.0]), measurement_noise_fraction=1.5)


def test_rolling_zscore_matches_manual_calculation():
    series = pd.Series(np.arange(20, dtype=float))
    out = rolling_zscore(series, window=5, min_periods=5)
    manual = (series - series.rolling(5, min_periods=5).mean()) / series.rolling(5, min_periods=5).std()
    assert np.allclose(out.dropna().to_numpy(), manual.dropna().to_numpy())


def test_rolling_zscore_nan_on_flat_window():
    series = pd.Series([5.0] * 10)
    out = rolling_zscore(series, window=5, min_periods=5)
    assert out.iloc[5:].isna().all()


def test_add_kalman_deviation_leaves_execution_columns_untouched():
    idx = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": np.linspace(1.0, 1.1, 10),
            "high": np.linspace(1.01, 1.11, 10),
            "low": np.linspace(0.99, 1.09, 10),
            "close": np.linspace(1.0, 1.1, 10) + np.array([0, 0.01, -0.01, 0, 0.02, -0.02, 0, 0.01, -0.01, 0]),
            "vwap": np.linspace(1.0, 1.1, 10),
        },
        index=idx,
    )
    out = add_kalman_deviation(df)

    assert "close_kalman" in out.columns and "deviation_kalman" in out.columns
    assert np.allclose(out["close"].to_numpy(), df["close"].to_numpy())
    assert np.allclose(out["vwap"].to_numpy(), df["vwap"].to_numpy())
    assert np.allclose(out["open"].to_numpy(), df["open"].to_numpy())


def test_add_kalman_deviation_requires_vwap_column():
    df = pd.DataFrame({"close": [1.0, 1.1, 1.2]})
    with pytest.raises(ValueError):
        add_kalman_deviation(df)
