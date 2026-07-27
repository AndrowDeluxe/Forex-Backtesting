import pandas as pd
import pytest

from strategy.backtest import BacktestConfig, simulate_trades

CFG = BacktestConfig(spread_bps=2.0, stop_atr_mult=0.5)


def _make_df(open_, close_, vwap_, atr_, prev_high_, prev_low_, signal_, session_, adx_=None):
    idx = pd.date_range("2024-01-01", periods=len(open_), freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": open_, "close": close_, "vwap": vwap_, "atr": atr_,
            "prev_high": prev_high_, "prev_low": prev_low_, "signal": signal_,
            "session": session_, "adx": adx_ or [30.0] * len(open_),
        },
        index=idx,
    )


def test_entry_executes_at_next_bar_open_not_signal_bar_close():
    df = _make_df(
        open_=[1.000, 1.000, 1.000],
        close_=[1.010, 1.000, 0.990],  # bar0 close (would be look-ahead if used) differs from bar1 open
        vwap_=[0.995, 0.995, 0.995],
        atr_=[0.01, 0.01, 0.01],
        prev_high_=[0.999, 0.999, 0.999],
        prev_low_=[0.90, 0.90, 0.90],
        signal_=[-1, 0, 0],
        session_=["A", "A", "A"],
    )
    trades = simulate_trades(df, CFG)
    assert len(trades) == 1
    assert trades.iloc[0]["entry_time"] == df.index[1]
    raw_entry = df["open"].iloc[1]
    expected_entry_price = raw_entry - raw_entry * (CFG.spread_bps / 10_000 / 2)
    assert trades.iloc[0]["entry_price"] == pytest.approx(expected_entry_price)


def test_short_trade_exits_on_vwap_cross_target_with_correct_pnl():
    df = _make_df(
        open_=[1.000, 1.000, 1.000],
        close_=[1.000, 1.000, 0.994],
        vwap_=[0.995, 0.995, 0.995],
        atr_=[0.01, 0.01, 0.01],
        prev_high_=[0.999, 0.999, 0.999],
        prev_low_=[0.90, 0.90, 0.90],
        signal_=[-1, 0, 0],
        session_=["A", "A", "A"],
    )
    trades = simulate_trades(df, CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "target"
    assert trade["exit_time"] == df.index[2]

    half = CFG.spread_bps / 10_000 / 2
    expected_entry = 1.000 - 1.000 * half
    expected_exit = 0.994 + 0.994 * half
    expected_ret = (expected_entry - expected_exit) / expected_entry
    assert trade["return_pct"] == pytest.approx(expected_ret)
    assert trade["return_pct"] > 0  # price fell after a short -> profit


def test_short_trade_stopped_out_above_prior_high_plus_atr_margin():
    df = _make_df(
        open_=[1.000, 1.000, 1.000],
        close_=[1.000, 1.000, 1.006],  # > prev_high(0.999) + 0.5*atr(0.01) = 1.004
        vwap_=[0.995, 0.995, 0.995],
        atr_=[0.01, 0.01, 0.01],
        prev_high_=[0.999, 0.999, 0.999],
        prev_low_=[0.90, 0.90, 0.90],
        signal_=[-1, 0, 0],
        session_=["A", "A", "A"],
    )
    trades = simulate_trades(df, CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "stop"
    assert trade["return_pct"] < 0  # stopped out -> loss


def test_position_forced_closed_at_session_rollover():
    df = _make_df(
        open_=[1.000, 1.000, 1.000],
        close_=[1.000, 1.000, 1.000],  # never hits stop or target
        vwap_=[0.995, 0.995, 0.995],
        atr_=[0.01, 0.01, 0.01],
        prev_high_=[0.999, 0.999, 0.999],
        prev_low_=[0.90, 0.90, 0.90],
        signal_=[-1, 0, 0],
        session_=["A", "A", "B"],  # session rolls over at bar 2
    )
    trades = simulate_trades(df, CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "session_end"
    assert trade["exit_time"] == df.index[1]  # last bar of the entry session


def test_no_new_entry_while_position_is_open():
    df = _make_df(
        open_=[1.000, 1.000, 1.000, 1.000, 1.000],
        close_=[1.000, 1.000, 1.000, 1.000, 0.994],
        vwap_=[0.995] * 5,
        atr_=[0.01] * 5,
        prev_high_=[0.999] * 5,
        prev_low_=[0.90] * 5,
        signal_=[-1, -1, -1, 0, 0],  # repeated signal while already in a trade
        session_=["A"] * 5,
    )
    trades = simulate_trades(df, CFG)
    assert len(trades) == 1
