import pandas as pd

from checklist_strategy.signals import generate_checklist_signals


def _base_df(n=30):
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "close": 1.1000,
            "env_upper": 1.1010, "env_lower": 1.0990,
            "avg_rsi": 50.0,
            "rsi": 50.0, "rsi_ma": 50.0,
        },
        index=idx,
    )


def test_full_chain_fires_short_entry():
    df = _base_df()
    # bar 5: breakout above upper band -> stage 1, short bias
    df.loc[df.index[5], "close"] = 1.1020
    # bar 6: RSI-multi-length crosses above 70 -> stage 2
    df.loc[df.index[6], "avg_rsi"] = 75.0
    # bar 7: rsi was >70 (bar 6) and crosses below its MA on bar 7 -> entry
    df.loc[df.index[6], ["rsi", "rsi_ma"]] = [72.0, 60.0]  # rsi > rsi_ma, both >70 context
    df.loc[df.index[7], ["rsi", "rsi_ma"]] = [58.0, 60.0]  # rsi <= rsi_ma now: cross down

    out = generate_checklist_signals(df)
    assert out["signal"].iloc[7] == -1
    assert (out["signal"].drop(out.index[7]) == 0).all()


def test_full_chain_fires_long_entry_symmetrically():
    df = _base_df()
    df.loc[df.index[5], "close"] = 1.0980  # breaks lower band -> long bias
    df.loc[df.index[6], "avg_rsi"] = 25.0  # crosses below 30 -> stage 2
    df.loc[df.index[6], ["rsi", "rsi_ma"]] = [28.0, 40.0]  # rsi < rsi_ma, both <30 context
    df.loc[df.index[7], ["rsi", "rsi_ma"]] = [45.0, 40.0]  # rsi >= rsi_ma: cross up

    out = generate_checklist_signals(df)
    assert out["signal"].iloc[7] == 1


def test_confirmation1_expires_before_confirmation2():
    df = _base_df()
    df.loc[df.index[5], "close"] = 1.1020  # stage 1 at bar 5
    # confirmation 2 arrives after the default 8-bar expiry (bar 5 + 9 = 14)
    df.loc[df.index[14], "avg_rsi"] = 75.0
    df.loc[df.index[14], ["rsi", "rsi_ma"]] = [72.0, 60.0]
    df.loc[df.index[15], ["rsi", "rsi_ma"]] = [58.0, 60.0]

    out = generate_checklist_signals(df, confirm1_expiry_bars=8)
    assert (out["signal"] == 0).all()


def test_opposite_breakout_overrides_bias_and_discards_progress():
    df = _base_df()
    df.loc[df.index[5], "close"] = 1.1020  # short bias armed
    df.loc[df.index[6], "avg_rsi"] = 75.0  # short confirmed (stage 2)
    df.loc[df.index[7], "close"] = 1.0980  # opposite breakout -> long bias, back to stage 1
    # Now try to fire what would have been the short entry trigger - must NOT fire,
    # since bias flipped to long and stage reset to 1 (confirmation 2 not yet re-done).
    df.loc[df.index[7], ["rsi", "rsi_ma"]] = [72.0, 60.0]
    df.loc[df.index[8], ["rsi", "rsi_ma"]] = [58.0, 60.0]

    out = generate_checklist_signals(df)
    assert (out["signal"] == 0).all()


def test_same_direction_retouch_refreshes_timer_instead_of_resetting_stage():
    df = _base_df()
    df.loc[df.index[5], "close"] = 1.1020  # stage 1, short bias, stage_bar=5
    df.loc[df.index[6], "avg_rsi"] = 75.0  # stage 2 at bar 6
    # Re-touch the SAME (upper) band at bar 10 - should refresh the stage-2
    # expiry clock, not force back down to stage 1.
    df.loc[df.index[10], "close"] = 1.1020
    # Confirmation-2 level condition must still hold (it's a level check, not edge-triggered).
    df.loc[df.index[10], "avg_rsi"] = 75.0
    # Entry trigger well within 8 bars of the refreshed stage_bar (10), but
    # more than 8 bars after the original stage-2 bar (6) - only passes if
    # the retouch actually refreshed the clock.
    df.loc[df.index[16], ["rsi", "rsi_ma"]] = [72.0, 60.0]
    df.loc[df.index[17], ["rsi", "rsi_ma"]] = [58.0, 60.0]

    out = generate_checklist_signals(df, confirm2_expiry_bars=8)
    assert out["signal"].iloc[17] == -1


def test_regime_filter_blocks_entry_when_regime_ok_is_false():
    df = _base_df()
    df["regime_ok"] = True
    df.loc[df.index[5], "close"] = 1.1020
    df.loc[df.index[6], "avg_rsi"] = 75.0
    df.loc[df.index[6], ["rsi", "rsi_ma"]] = [72.0, 60.0]
    df.loc[df.index[7], ["rsi", "rsi_ma"]] = [58.0, 60.0]
    df.loc[df.index[7], "regime_ok"] = False  # regime says no at the exact trigger bar

    out = generate_checklist_signals(df, require_regime_ok=True)
    assert out["signal"].iloc[7] == 0


def test_regime_filter_allows_entry_when_regime_ok_is_true():
    df = _base_df()
    df["regime_ok"] = True
    df.loc[df.index[5], "close"] = 1.1020
    df.loc[df.index[6], "avg_rsi"] = 75.0
    df.loc[df.index[6], ["rsi", "rsi_ma"]] = [72.0, 60.0]
    df.loc[df.index[7], ["rsi", "rsi_ma"]] = [58.0, 60.0]

    out = generate_checklist_signals(df, require_regime_ok=True)
    assert out["signal"].iloc[7] == -1
