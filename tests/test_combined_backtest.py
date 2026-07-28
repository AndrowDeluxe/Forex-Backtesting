import numpy as np
import pandas as pd

from combined_strategy.backtest import simulate_trades


def _make_df(n=20):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC", name="Date")
    df = pd.DataFrame(
        {
            "Open": 1.000, "High": 1.002, "Low": 0.998, "Close": 1.000,
            "trigger_ema": 0.5,  # always below Close -> no price-based trend invalidation
            "daily_bias": 1,
            "signal": 0,
            "daily_adx": 20.0,
        },
        index=idx,
    )
    df.loc[df.index[15], "signal"] = 1
    # ADX at/after entry: elevated at signal bar, rises once, then falls two bars running.
    df.loc[df.index[15], "daily_adx"] = 30.0
    df.loc[df.index[16], "daily_adx"] = 32.0
    df.loc[df.index[17], "daily_adx"] = 31.0
    df.loc[df.index[18], "daily_adx"] = 29.0
    return df


def test_adx_exhaustion_exit_triggers_after_confirm_bars():
    df = _make_df()
    trades, _ = simulate_trades(
        df, exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0,
        adx_exhaustion_confirm_bars=2,
    )
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["reason"] == "ADX-Erschöpfung"
    assert trade["exit_time"] == df.index[18]


def test_adx_exhaustion_exit_disabled_by_default_lets_trade_run():
    df = _make_df()
    trades, _ = simulate_trades(df)  # exit_on_adx_exhaustion=False by default
    # No SL/TP/trend-invalidation ever fires in this fixture, so without the
    # new exit the position should still be open (no closed trade recorded)
    # by the time the data ends.
    assert trades.empty


def test_adx_exhaustion_not_triggered_when_entry_adx_below_threshold():
    df = _make_df()
    df.loc[df.index[15], "daily_adx"] = 15.0  # below the 25.0 entry threshold
    trades, _ = simulate_trades(
        df, exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0,
        adx_exhaustion_confirm_bars=2,
    )
    assert trades.empty
