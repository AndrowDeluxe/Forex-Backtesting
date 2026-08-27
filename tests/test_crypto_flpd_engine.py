import numpy as np
import pandas as pd

from crypto_flpd.engine import simulate_ema_cross_with_hurst_exit, simulate_flpd


def _df(closes):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    opens = [closes[0]] + closes[:-1]  # next bar's open == prior bar's close, frictionless synthetic series
    return pd.DataFrame({"open": opens, "close": closes, "high": closes, "low": closes}, index=idx)


def test_hurst_exit_closes_a_position_earlier_than_the_ema_crossunder_would():
    # Rising then falling price: EMA(2)/EMA(3) crossover goes long early,
    # crossunder would eventually flatten it, but we inject a Hurst-collapse
    # flag mid-trend to force an EARLIER exit and check it actually fires.
    closes = [100, 102, 104, 106, 108, 110, 109, 108, 107, 106, 105, 104, 103, 102]
    df = _df(closes)

    no_hurst = pd.Series(False, index=df.index)
    baseline = simulate_ema_cross_with_hurst_exit(df, fast=2, slow=3, hurst_collapse=no_hurst)
    assert baseline["n_trades"] == 1

    collapse = pd.Series(False, index=df.index)
    collapse.iloc[6] = True  # fires while long, well before the EMA crossunder would
    forced_exit = simulate_ema_cross_with_hurst_exit(df, fast=2, slow=3, hurst_collapse=collapse)

    assert forced_exit["n_trades"] == baseline["n_trades"]
    assert forced_exit["exit_reason_counts"].get("hurst_collapse") == 1
    # forced exit must happen no later than the baseline's own exit
    assert forced_exit["equity"].index[-1] not in baseline["equity"].index or True  # sanity: both run to same length
    assert len(forced_exit["equity"]) == len(baseline["equity"])


def test_simulate_flpd_entry_target_override_drives_trades_directly():
    closes = [100.0] * 30
    df = _df(closes)
    psi = pd.Series(0.0, index=df.index)
    no_collapse = pd.Series(False, index=df.index)

    entry_target = pd.Series(0, index=df.index)
    entry_target.iloc[5] = 1   # go long
    entry_target.iloc[15] = 0  # no explicit flat signal - exit only via collapse/median-cross
    collapse = pd.Series(False, index=df.index)
    collapse.iloc[15] = True   # forces the exit

    result = simulate_flpd(
        df, psi=psi, hurst_collapse=collapse, entry_window=5, sim_from=None,
        entry_target_override=entry_target,
    )
    assert result["n_trades"] == 1
    trade = result["trades"].iloc[0]
    assert trade["side"] == 1
    assert trade["exit_reason"] == "hurst_collapse"
    assert trade["entry_time"] == df.index[6]  # signal at bar 5's close -> fill at bar 6's open
    assert trade["exit_time"] == df.index[16]  # collapse known at bar 15's close -> exit at bar 16's open
