import numpy as np
import pandas as pd
import pytest

from strategy.mtf_ema_ribbon import (
    apply_mtf_ribbon_filter,
    attach_mtf_ema_ribbon,
    htf_ema,
    resample_close,
    ribbon_bias,
)


def _hourly_close(n=24 * 40, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = pd.Series(100 + np.cumsum(rng.normal(0, 0.1, n)), index=idx)
    return close


def test_resample_close_uses_last_price_per_bar():
    idx = pd.date_range("2024-01-01 01:00", periods=6, freq="h", tz="UTC")
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], index=idx)
    daily = resample_close(close, "1D")
    assert len(daily) == 1
    assert daily.iloc[0] == pytest.approx(6.0)


def test_htf_ema_no_lookahead():
    close = _hourly_close()
    full = htf_ema(close, "1D", 10)
    # +1 so the truncated series ends exactly on a daily boundary -- its last
    # bin is then fully closed too, not a still-forming partial bin (which
    # would legitimately differ from the full series' value for that same
    # bin, since a forming bar's tentative value keeps changing as more
    # intrabar data arrives -- that's not a lookahead bug, just an unclosed bar)
    truncated = htf_ema(close.iloc[: 24 * 20 + 1], "1D", 10)
    common = full.index.intersection(truncated.index)
    assert len(common) > 5
    assert np.allclose(full.loc[common].to_numpy(), truncated.loc[common].to_numpy())


def test_attach_mtf_ema_ribbon_adds_one_column_per_level():
    close = _hourly_close()
    df = pd.DataFrame({"close": close})
    levels = [("ema_4h", "4h", 20), ("ema_1d", "1D", 10)]
    out = attach_mtf_ema_ribbon(df, levels=levels)
    assert "ema_4h" in out.columns and "ema_1d" in out.columns
    assert len(out) == len(df)
    assert out.index.equals(df.index)


def test_attach_mtf_ema_ribbon_only_sees_closed_htf_bars():
    close = _hourly_close()
    df = pd.DataFrame({"close": close})
    levels = [("ema_1d", "1D", 10)]
    out = attach_mtf_ema_ribbon(df, levels=levels)
    daily_ema = htf_ema(close, "1D", 10)

    # a row in the middle of day 3 must carry day 2's already-closed EMA
    # (label "2024-01-03"), never a value that used day 3's own (still
    # forming) bars
    mid_day3 = pd.Timestamp("2024-01-03 03:00", tz="UTC")
    day2_closed = daily_ema.loc[pd.Timestamp("2024-01-03 00:00", tz="UTC")]
    day3_closed = daily_ema.loc[pd.Timestamp("2024-01-04 00:00", tz="UTC")]
    assert out.loc[mid_day3, "ema_1d"] == pytest.approx(day2_closed)
    assert out.loc[mid_day3, "ema_1d"] != pytest.approx(day3_closed)


def test_ribbon_bias_bullish_when_price_above_all_emas():
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {"close": [10.0, 10.0, 10.0], "ema_a": [9.0, 9.0, 9.0], "ema_b": [8.0, 8.0, 8.0]}, index=idx
    )
    bias = ribbon_bias(df, levels=[("ema_a", "1D", 1), ("ema_b", "1D", 1)])
    assert (bias == 1).all()


def test_ribbon_bias_bearish_when_price_below_all_emas():
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {"close": [5.0, 5.0, 5.0], "ema_a": [9.0, 9.0, 9.0], "ema_b": [8.0, 8.0, 8.0]}, index=idx
    )
    bias = ribbon_bias(df, levels=[("ema_a", "1D", 1), ("ema_b", "1D", 1)])
    assert (bias == -1).all()


def test_ribbon_bias_neutral_when_emas_disagree_or_missing():
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {"close": [10.0, 10.0], "ema_a": [9.0, np.nan], "ema_b": [11.0, 8.0]}, index=idx
    )
    bias = ribbon_bias(df, levels=[("ema_a", "1D", 1), ("ema_b", "1D", 1)])
    assert bias.iloc[0] == 0  # disagreement: above ema_a, below ema_b
    assert bias.iloc[1] == 0  # missing ema_a value


def test_apply_mtf_ribbon_filter_zeros_counter_trend_positions():
    position = pd.Series([1, -1, 1, -1, 0])
    bias = pd.Series([1, -1, -1, 1, 1])
    filtered = apply_mtf_ribbon_filter(position, bias)
    assert filtered.tolist() == [1, -1, 0, 0, 0]
