"""The Opening Range itself: high/low of the first `range_bars` M15 bar(s)
starting at the 09:30 NY cash-equity open, broadcast onto a (possibly
finer-timeframe) execution frame for the rest of that session.

Deliberately session-scoped (one range per calendar day in NY-local time,
`data.py` already converts the index there) rather than tied to a fixed UTC
hour - see data.py's docstring for why a fixed UTC hour would drift across
US/EU daylight-saving transitions.
"""

import numpy as np
import pandas as pd

NY_OPEN_HOUR, NY_OPEN_MINUTE = 9, 30
NY_CLOSE_HOUR, NY_CLOSE_MINUTE = 16, 0


def compute_session_range(m15: pd.DataFrame, range_bars: int = 1) -> pd.DataFrame:
    """One row per session (index = session date at NY midnight) with
    orb_high/orb_low/orb_width and `range_end` - the NY-local timestamp at
    which the range bar(s) close, i.e. the earliest moment any signal may
    fire (no lookahead into the range-forming bar itself)."""
    session = m15.index.normalize()
    minutes = m15.index.hour * 60 + m15.index.minute
    open_min = NY_OPEN_HOUR * 60 + NY_OPEN_MINUTE
    in_range = (minutes >= open_min) & (minutes < open_min + 15 * range_bars)

    range_bars_df = m15.loc[in_range]
    if range_bars_df.empty:
        return pd.DataFrame(columns=["orb_high", "orb_low", "orb_width", "range_end"])

    grouped = range_bars_df.groupby(session[in_range])
    result = grouped.agg(orb_high=("high", "max"), orb_low=("low", "min"))
    result["orb_width"] = result["orb_high"] - result["orb_low"]
    result["range_end"] = (
        result.index
        + pd.Timedelta(hours=NY_OPEN_HOUR, minutes=NY_OPEN_MINUTE)
        + pd.Timedelta(minutes=15 * range_bars)
    )
    return result


def attach_orb_levels(df: pd.DataFrame, session_range: pd.DataFrame) -> pd.DataFrame:
    """Broadcasts each session's orb_high/orb_low/orb_width/range_end onto
    every bar of that session, for any execution timeframe (`df` can be M15
    or M5). Bars before `range_end` (including the range-forming bar(s)
    themselves) get NaN levels - nothing tradeable yet. Also attaches
    `session` (NY midnight of that bar) and `session_close` (that day's
    16:00 NY cash close, the hard end-of-session exit boundary)."""
    out = df.copy()
    session = out.index.normalize()
    out["session"] = session
    out["session_close"] = session + pd.Timedelta(hours=NY_CLOSE_HOUR, minutes=NY_CLOSE_MINUTE)

    out["orb_high"] = session.map(session_range["orb_high"])
    out["orb_low"] = session.map(session_range["orb_low"])
    out["orb_width"] = session.map(session_range["orb_width"])
    out["range_end"] = session.map(session_range["range_end"])

    not_yet_formed = out.index < out["range_end"]
    out.loc[not_yet_formed, ["orb_high", "orb_low", "orb_width"]] = np.nan
    return out
