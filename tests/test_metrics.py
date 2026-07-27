import pandas as pd
import pytest

from strategy.backtest import BacktestConfig
from strategy.metrics import breakeven_spread_bps


def _single_short_trade_df():
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [1.000, 1.000, 1.000],
            "close": [1.000, 1.000, 0.994],
            "vwap": [0.995, 0.995, 0.995],
            "atr": [0.01, 0.01, 0.01],
            "prev_high": [0.999, 0.999, 0.999],
            "prev_low": [0.90, 0.90, 0.90],
            "signal": [-1, 0, 0],
            "session": ["A", "A", "A"],
            "adx": [30.0, 30.0, 30.0],
        },
        index=idx,
    )


def test_breakeven_spread_matches_closed_form_solution():
    # Regression guard: an earlier version used an absolute-return tolerance
    # (1e-3) that is far coarser than typical trade returns (~1e-4), which
    # made the bisection falsely "converge" on its very first midpoint.
    df = _single_short_trade_df()
    base_config = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)

    raw_entry, raw_exit = 1.000, 0.994
    h_breakeven = (raw_entry - raw_exit) / (raw_entry + raw_exit)
    expected_bps = h_breakeven * 20_000

    result = breakeven_spread_bps(df, base_config, lo=0.0, hi=200.0)
    assert result == pytest.approx(expected_bps, abs=0.05)
