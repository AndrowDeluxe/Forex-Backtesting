"""Post-hoc filters for auction_playbook trades - same pattern as
asian_range_breakout/filters.py::attach_trend_bias/apply_trend_bias_filter.
Dropping a trade here is equivalent to never having entered it (each setup
is an independent event triggered by the state machine in signals.py), so
filtering doesn't need to re-run the state machine."""

import pandas as pd

from crypto_flpd.phases import trend_state


def attach_htf_trend_bias(
    trades: pd.DataFrame, htf_close: pd.Series, htf_bar_duration: pd.Timedelta, fast: int = 9, slow: int = 21
) -> pd.DataFrame:
    """Attaches an `aligned` boolean column: True if the trade's direction
    matches the prevailing HIGHER-TIMEFRAME trend (EMA(fast) > EMA(slow) on
    `htf_close`, e.g. 4h/Daily bias for these 5m auction_playbook trades) -
    structurally identical to asian_range_breakout/filters.py's SMA200
    trend-bias filter for Gold, just crypto_flpd.phases.trend_state (EMA9/21
    on a higher-timeframe bar) instead of a daily SMA. Applies to BOTH
    setups (trend_continuation and mean_reversion) the same way: does this
    trade's own direction (not its setup type) agree with the bigger-picture
    trend, exactly as attach_trend_bias treats direction-agnostic of setup.

    No-lookahead: `auction_playbook.data.fetch_klines` indexes each bar by
    its OPEN time, so a HTF bar's trend state is only knowable once that bar
    CLOSES. The state series is shifted forward by one `htf_bar_duration`
    before being matched via merge_asof (most recent HTF state STRICTLY AT
    OR BEFORE the trade's entry_time, backward direction) - same prior-
    period discipline as asian_range_breakout/filters.py's day-lagged joins
    and crypto_flpd.phases.psi_matrix's HTF->LTF reindex, at bar-duration
    granularity here."""
    state = trend_state(htf_close, fast=fast, slow=slow)
    known_at = state.copy()
    known_at.index = known_at.index + htf_bar_duration
    known_at_df = known_at.rename("htf_bullish").to_frame()
    # entry_time (from klines' ms-resolution timestamps) and the shifted HTF
    # index (whose resolution can drift once a Timedelta is added) sometimes
    # land on different datetime64 resolutions ([ms] vs [us]/[ns]) - pandas
    # merge_asof refuses to join across resolutions, so both keys are
    # normalized to a common resolution first.
    known_at_df.index = known_at_df.index.as_unit("ns")

    out = trades.sort_values("entry_time").reset_index(drop=True)
    out["entry_time"] = out["entry_time"].dt.as_unit("ns")
    merged = pd.merge_asof(out, known_at_df, left_on="entry_time", right_index=True, direction="backward")
    merged = merged.dropna(subset=["htf_bullish"])

    is_long = merged["direction"] == 1
    merged["aligned"] = (is_long & merged["htf_bullish"]) | (~is_long & ~merged["htf_bullish"])
    return merged


def apply_htf_trend_bias_filter(
    trades: pd.DataFrame, htf_close: pd.Series, htf_bar_duration: pd.Timedelta, fast: int = 9, slow: int = 21
) -> pd.DataFrame:
    """Drops trades whose direction disagrees with the HTF trend bias (see
    attach_htf_trend_bias)."""
    out = attach_htf_trend_bias(trades, htf_close, htf_bar_duration, fast=fast, slow=slow)
    return out[out["aligned"]]
