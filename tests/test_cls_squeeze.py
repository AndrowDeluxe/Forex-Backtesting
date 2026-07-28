import pandas as pd

from strategy.indicators import compute_intraday_window_extremes
from strategy.cls_squeeze import generate_cls_squeeze_signal


def test_intraday_window_extremes_nan_before_running_during_frozen_after():
    idx = pd.date_range("2024-01-01 05:00", periods=6, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 6, "close": [1.0] * 6,
            "high": [1.00, 1.02, 1.05, 1.01, 1.03, 1.03],
            "low": [1.00, 0.99, 0.97, 0.98, 0.96, 0.96],
        },
        index=idx,
    )
    # hours: 05,06,07,08,09,10 -> window [06,08)
    out = compute_intraday_window_extremes(df, window_start_hour=6, window_end_hour=8)

    assert pd.isna(out["window_high"].iloc[0])  # 05:00, before window
    assert out["window_high"].iloc[1] == 1.02   # 06:00, running max so far
    assert out["window_high"].iloc[2] == 1.05   # 07:00, running max updates
    assert out["window_high"].iloc[3] == 1.05   # 08:00, frozen at window close
    assert out["window_high"].iloc[5] == 1.05   # 10:00, still frozen

    assert pd.isna(out["window_low"].iloc[0])
    assert out["window_low"].iloc[1] == 0.99
    assert out["window_low"].iloc[2] == 0.97
    assert out["window_low"].iloc[3] == 0.97
    assert out["window_low"].iloc[5] == 0.97


def test_intraday_window_extremes_do_not_leak_across_days():
    idx = pd.date_range("2024-01-01 06:00", periods=2, freq="D", tz="UTC")
    df = pd.DataFrame({"open": [1.0, 1.0], "close": [1.0, 1.0], "high": [1.10, 1.00], "low": [0.90, 1.00]}, index=idx)
    out = compute_intraday_window_extremes(df, window_start_hour=6, window_end_hour=7)
    # Day 2 (lower range) must not inherit day 1's much wider high/low.
    assert out["window_high"].iloc[1] == 1.00
    assert out["window_low"].iloc[1] == 1.00


def _signal_df():
    idx = pd.date_range("2024-01-01 06:55", periods=4, freq="5min", tz="UTC")  # 06:55,07:00,07:05,07:10
    df = pd.DataFrame(
        {
            "close": 1.10, "deviation": 0.003, "theta": 0.002,
            "adx": 30.0, "adx_mean": 25.0, "delta_adx": -0.5,
            "window_high": 1.09, "window_low": 1.00,
        },
        index=idx,
    )
    return df


def test_signal_fires_inside_entry_window():
    df = _signal_df()
    out = generate_cls_squeeze_signal(df, entry_start_hour=7.0, entry_end_hour=7.5, theta=df["theta"])
    assert out["signal"].iloc[1] == -1  # 07:00, inside [7.0, 7.5)


def test_signal_suppressed_before_entry_window_even_if_conditions_met():
    df = _signal_df()
    out = generate_cls_squeeze_signal(df, entry_start_hour=7.0, entry_end_hour=7.5, theta=df["theta"])
    assert out["signal"].iloc[0] == 0  # 06:55, before entry window


def test_signal_suppressed_after_entry_window():
    df = _signal_df()
    out = generate_cls_squeeze_signal(df, entry_start_hour=7.0, entry_end_hour=7.05, theta=df["theta"])
    assert out["signal"].iloc[2] == 0  # 07:05, entry window already [7.0, 7.05) closed


def test_momentum_mode_flips_direction_vs_reversion():
    df = _signal_df()  # at window_high (1.09) with positive deviation
    reversion = generate_cls_squeeze_signal(df, 7.0, 7.5, theta=df["theta"], direction_mode="reversion")
    momentum = generate_cls_squeeze_signal(df, 7.0, 7.5, theta=df["theta"], direction_mode="momentum")
    assert reversion["signal"].iloc[1] == -1  # fade the high -> short
    assert momentum["signal"].iloc[1] == 1    # ride the breakout -> long


def test_invalid_direction_mode_raises():
    df = _signal_df()
    try:
        generate_cls_squeeze_signal(df, 7.0, 7.5, theta=df["theta"], direction_mode="sideways")
        assert False, "expected ValueError"
    except ValueError:
        pass
