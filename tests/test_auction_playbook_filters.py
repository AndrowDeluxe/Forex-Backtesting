import pandas as pd

from auction_playbook.filters import attach_htf_trend_bias, apply_htf_trend_bias_filter


def _htf_close_bullish_from_bar2():
    # 3 HTF (4h) bars: flat/bearish, then a bullish EMA(1)/EMA(2) state from
    # the 2nd bar onward (single-period EMA reacts immediately to price).
    idx = pd.date_range("2024-01-01 00:00", periods=3, freq="4h", tz="UTC")
    close = pd.Series([100.0, 90.0, 200.0], index=idx)  # EMA(1)=close, so state flips exactly at bar 3 (200 > EMA(2))
    return close


def test_attach_htf_trend_bias_is_causal_not_visible_before_htf_close():
    htf_close = _htf_close_bullish_from_bar2()
    # HTF bar 3 (08:00-12:00) is the one whose CLOSE flips the state bullish.
    trades = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(
                ["2024-01-01 09:00", "2024-01-01 11:59", "2024-01-01 12:00", "2024-01-01 15:00"], utc=True
            ),
            "direction": [1, 1, 1, 1],
        }
    )
    out = attach_htf_trend_bias(trades, htf_close, htf_bar_duration=pd.Timedelta("4h"), fast=1, slow=2)
    # Entries strictly inside the still-forming HTF bar 3 (09:00, 11:59) must
    # only see bar 2's (still-bearish) state, not bar 3's not-yet-closed one.
    assert out.loc[out["entry_time"] == pd.Timestamp("2024-01-01 09:00", tz="UTC"), "htf_bullish"].iloc[0] == False
    assert out.loc[out["entry_time"] == pd.Timestamp("2024-01-01 11:59", tz="UTC"), "htf_bullish"].iloc[0] == False
    # Entries at/after bar 3's close (12:00) see the now-known bullish state.
    assert out.loc[out["entry_time"] == pd.Timestamp("2024-01-01 12:00", tz="UTC"), "htf_bullish"].iloc[0] == True
    assert out.loc[out["entry_time"] == pd.Timestamp("2024-01-01 15:00", tz="UTC"), "htf_bullish"].iloc[0] == True


def test_aligned_flags_long_with_bullish_and_short_with_bearish():
    htf_close = _htf_close_bullish_from_bar2()
    trades = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(["2024-01-01 12:00", "2024-01-01 12:00"], utc=True),
            "direction": [1, -1],
        }
    )
    out = attach_htf_trend_bias(trades, htf_close, htf_bar_duration=pd.Timedelta("4h"), fast=1, slow=2)
    long_row = out[out["direction"] == 1].iloc[0]
    short_row = out[out["direction"] == -1].iloc[0]
    assert long_row["aligned"] == True   # long while HTF bullish -> aligned
    assert short_row["aligned"] == False  # short while HTF bullish -> NOT aligned


def test_apply_filter_drops_misaligned_trades():
    htf_close = _htf_close_bullish_from_bar2()
    trades = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(["2024-01-01 12:00", "2024-01-01 12:00"], utc=True),
            "direction": [1, -1],
        }
    )
    out = apply_htf_trend_bias_filter(trades, htf_close, htf_bar_duration=pd.Timedelta("4h"), fast=1, slow=2)
    assert len(out) == 1
    assert out.iloc[0]["direction"] == 1
