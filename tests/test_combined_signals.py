import pandas as pd

from combined_strategy.signals import build_signals


def _base_df(n=60):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": 1.000, "High": 1.001, "Low": 0.999, "Close": 1.000, "Volume": 100.0,
            "weekly_bias": 1, "daily_bias": 1,
            "deviation": 0.0, "prev_high": 2.0, "prev_low": 0.0,
        },
        index=idx,
    )
    # Signal bar: dips below the (converged, constant) EMA and closes back above it.
    df.loc[df.index[-1], ["Low", "Close"]] = [0.997, 1.0005]
    return df


def test_baseline_long_signal_fires_without_filters():
    df = _base_df()
    out = build_signals(df)
    assert out["signal"].iloc[-1] == 1


def test_vwap_filter_suppresses_overextended_long():
    df = _base_df()
    df.loc[df.index[-1], "deviation"] = 1.0  # wildly overextended vs. the ~0 rolling history
    out = build_signals(df, use_vwap_filter=True, vwap_theta_window_bars=20, vwap_theta_multiplier=1.0)
    assert out["signal"].iloc[-1] == 0


def test_vwap_filter_allows_non_overextended_long():
    df = _base_df()  # deviation stays 0.0 throughout, never overextended
    out = build_signals(df, use_vwap_filter=True, vwap_theta_window_bars=20, vwap_theta_multiplier=1.0)
    assert out["signal"].iloc[-1] == 1


def test_session_confluence_filter_rejects_signal_far_from_any_extreme():
    df = _base_df()  # prev_high=2.0, prev_low=0.0 - both far from close ~1.0
    out = build_signals(df, use_session_confluence_filter=True, confluence_atr_mult=1.0)
    assert out["signal"].iloc[-1] == 0


def test_session_confluence_filter_allows_signal_near_prior_low():
    df = _base_df()
    df.loc[df.index[-1], "prev_low"] = 0.9998  # well within ~1 ATR (~0.002) of the signal close
    out = build_signals(df, use_session_confluence_filter=True, confluence_atr_mult=1.0)
    assert out["signal"].iloc[-1] == 1
