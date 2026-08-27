"""Relative Volume at Time - the one indicator genuinely new to this repo
for this strategy. ATR/ADX (strategy/indicators.py) and the M5 fractal
(gold_smc_htf_ltf/structure.py::detect_fractal_swings) are reused directly
by engine.py rather than re-exported here through a pointless wrapper.
"""

import pandas as pd


def relative_volume_at_time(df: pd.DataFrame, lookback_days: int = 20) -> pd.DataFrame:
    """Bar volume divided by the trailing average volume at the SAME
    time-of-day (HH:MM) over the prior `lookback_days` occurrences of that
    time slot - e.g. the 09:35 bar is compared only against prior days'
    09:35 bars, not a blunt N-bar trailing average blind to time-of-day
    (that's what orb_strategy/pipeline.py's `volume_ratio` already is - see
    its own docstring calling that out as "not a precise same-time-of-day
    seasonal baseline"). This matters intraday because volume has a strong
    time-of-day seasonal shape (busy at the open/close, quiet at midday),
    which a plain rolling average blurs.

    Grouping by HH:MM string preserves each time slot's own chronological
    sub-sequence (one occurrence per session), so `.shift(1).rolling(n)` on
    that sub-sequence is exactly "the trailing n prior days' bar at this
    same clock time" - no lookahead, since a day's own bar is shifted out of
    its own baseline before the rolling window is computed.

    Adds `volume_avg_at_time` and `rvol_at_time` (NaN until `lookback_days`
    prior occurrences exist).
    """
    out = df.copy()
    time_of_day = out.index.strftime("%H:%M")
    grouped_volume = out.groupby(time_of_day)["volume"]
    min_periods = max(lookback_days // 2, 1)
    out["volume_avg_at_time"] = grouped_volume.transform(
        lambda s: s.shift(1).rolling(lookback_days, min_periods=min_periods).mean()
    )
    out["rvol_at_time"] = out["volume"] / out["volume_avg_at_time"]
    return out
