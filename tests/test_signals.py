import pandas as pd

from strategy.signals import generate_signal


def _row(**overrides):
    base = dict(
        close=1.10, prev_high=1.09, prev_low=1.00, deviation=0.003,
        theta=0.002, adx=30.0, adx_mean=25.0, delta_adx=-0.5,
    )
    base.update(overrides)
    return base


def _df(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="h", tz="UTC")
    return pd.DataFrame(rows, index=idx)


def test_all_four_conditions_true_gives_short_signal():
    df = _df([_row()])
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == -1


def test_symmetric_long_signal_at_prior_low():
    df = _df([_row(close=0.99, prev_low=1.00, deviation=-0.003)])
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == 1


def test_missing_spatial_condition_suppresses_signal():
    df = _df([_row(close=1.05)])  # not at/above prev_high anymore
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == 0


def test_missing_vwap_overextension_suppresses_signal():
    df = _df([_row(deviation=0.001)])  # below theta
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == 0


def test_rising_adx_suppresses_signal_even_if_elevated():
    df = _df([_row(delta_adx=0.5)])  # trend still strengthening
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == 0


def test_adx_not_elevated_suppresses_signal():
    df = _df([_row(adx=20.0, adx_mean=25.0)])
    out = generate_signal(df, theta=df["theta"])
    assert out["signal"].iloc[0] == 0
