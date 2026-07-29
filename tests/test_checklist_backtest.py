import pandas as pd
import pytest

from checklist_strategy.backtest import simulate_checklist_trades

CFG = dict(spread_bps=2.0, stop_atr_mult=2.5, rr_target=2.0, breakeven_at_r=1.0)


def _make_df(n, signal_at=None, signal_dir=None):
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    # Tight default range around 1.1000: high stays under the original stop
    # (~1.10239) and low stays above the original breakeven trigger
    # (~1.09739) for every un-overridden bar, so only explicitly-set bars
    # in each test actually move price.
    df = pd.DataFrame(
        {"open": 1.1000, "high": 1.1002, "low": 1.0998, "close": 1.1000, "atr": 0.0010, "signal": 0},
        index=idx,
    )
    if signal_at is not None:
        df.loc[df.index[signal_at], "signal"] = signal_dir
    return df


def test_entry_executes_at_next_bar_open():
    df = _make_df(10, signal_at=2, signal_dir=-1)
    trades = simulate_checklist_trades(df, **CFG)
    assert len(trades) == 1
    assert trades.iloc[0]["entry_time"] == df.index[3]


def test_short_trade_hits_stop():
    df = _make_df(20, signal_at=2, signal_dir=-1)
    # ATR(0.0010)*2.5 = 0.0025 stop distance above entry (~1.100).
    df.loc[df.index[5], "high"] = 1.1100  # blows well past the stop
    trades = simulate_checklist_trades(df, **CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "stop"
    assert trade["return_pct"] < 0


def test_short_trade_hits_target():
    df = _make_df(20, signal_at=2, signal_dir=-1)
    # TP = entry - 2*risk = entry - 0.0050 -> well below entry.
    df.loc[df.index[5], "low"] = 1.0900
    trades = simulate_checklist_trades(df, **CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "target"
    assert trade["return_pct"] > 0


def test_breakeven_move_then_stop_scratches_near_zero():
    df = _make_df(20, signal_at=2, signal_dir=-1)
    # Bar 5: price dips 1R favourable (low touches be_trigger = entry - 0.0025)
    # -> SL moves to entry. High is kept low too, so the move doesn't also
    # trip the new (breakeven) stop within this same bar.
    df.loc[df.index[5], ["low", "high"]] = [1.0970, 1.0980]
    # Bar 6 (and beyond) reverts to the default high (1.1002), which is
    # already above the entry price for a short (~1.09989) - triggers the
    # now-breakeven stop on the very next bar.
    trades = simulate_checklist_trades(df, **CFG)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "breakeven"
    assert bool(trade["moved_to_be"]) is True
    assert trade["return_pct"] == pytest.approx(0.0, abs=0.001)  # ~0 modulo the spread cost


def test_overlapping_trades_both_recorded_independently():
    df = _make_df(20)
    df.loc[df.index[2], "signal"] = -1
    df.loc[df.index[4], "signal"] = 1  # second signal while the first trade is still open
    trades = simulate_checklist_trades(df, **CFG)
    assert len(trades) == 2
    assert set(trades["direction"]) == {-1, 1}
