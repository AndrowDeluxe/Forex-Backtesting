"""London-Open 30-minute momentum signal (Seeck 2026). One row of output per
trading day with a resolvable signal -- this is a "one trade per day"
construction, structurally different from `strategy/backtest.py`'s
multi-bar VWAP/ADX state machine, so it gets its own small engine here
rather than forcing a reuse that doesn't fit.

Signal: r1 = log(close(entry_bar) / open(open_bar)), where open_bar is the
first M5 bar at/after 08:00 London-local time and entry_bar is the first M5
bar at/after 08:00 + `signal_minutes` (default 30) London-local time.
08:00 London-local is a DST-safe anchor via `tz_convert("Europe/London")`
(UK and EU clock changes are on the same last-Sunday-March/October
schedule, so 08:00 London is always exactly 09:00 Berlin -- no special
DST-transition-day handling needed beyond letting pandas do the conversion).

Open/entry bars are located by grouping on the LONDON-LOCAL calendar date,
not on this repo's usual UTC 22:00 "session" (reset_hour=22): a UTC-anchored
session spans two different London calendar dates (the tail ~1-2h of one
London day, then the bulk of the next), so London-local minute-of-day is
NOT monotonic within one UTC session -- searching "first bar with
london_minute >= 480" inside a UTC session would wrongly match the
session's own opening bars (late evening, numerically >= 480 despite being
hours before local midnight). Grouping by the London-local calendar date
avoids that wraparound entirely; the UTC session is only used afterwards,
to find the correct end-of-session exit bar for a given entry.
"""

import numpy as np
import pandas as pd

from strategy.indicators import assign_sessions

LONDON_OPEN_HOUR = 8
SIGNAL_MINUTES = 30


def _session_last_bar_lookup(df: pd.DataFrame) -> pd.Series:
    """Map session id -> timestamp of that session's last bar (df must be
    sorted and have a `session` column already)."""
    is_last_of_session = df["session"].ne(df["session"].shift(-1))
    is_last_of_session.iloc[-1] = True
    last_rows = df.loc[is_last_of_session]
    return pd.Series(last_rows.index, index=last_rows["session"].to_numpy())


def generate_london_momentum_trades(
    df: pd.DataFrame,
    reset_hour: int = 22,
    signal_minutes: int = SIGNAL_MINUTES,
    exit_after_minutes: int | None = None,
) -> pd.DataFrame:
    """df: M5 OHLCV, tz-aware UTC DatetimeIndex (Dukascopy's native format).

    `exit_after_minutes`: if None (default), hold to the close of the last
    bar of the entry's UTC session (reset_hour=22) -- the paper's own exact
    exit time within "the London-New York session" isn't given, so this
    reuses the repo's existing session-boundary convention as a disclosed
    default. If set, exit at the first bar at/after
    entry_time + exit_after_minutes instead (capped at the session's last
    bar if that point falls beyond it) -- a shorter, fixed-horizon
    robustness variant, since a same-day full-session hold is a much longer
    window than "intraday momentum" studies typically test.

    Returns one row per London-local calendar day with a resolvable signal:
    session, r1, direction, entry_time, entry_price, exit_time, exit_price,
    raw_return (log return, no costs -- see `costs.py` for cost-adjusted).
    """
    df = df.sort_index().copy()
    df["session"] = assign_sessions(df.index, reset_hour)
    london_local = df.index.tz_convert("Europe/London")
    df["_london_date"] = london_local.date
    df["_london_min"] = london_local.hour * 60 + london_local.minute

    session_exit = _session_last_bar_lookup(df)

    open_min = LONDON_OPEN_HOUR * 60
    entry_min = open_min + signal_minutes

    rows = []
    for _london_date, day_df in df.groupby("_london_date"):
        open_candidates = day_df.index[day_df["_london_min"] >= open_min]
        entry_candidates = day_df.index[day_df["_london_min"] >= entry_min]
        if open_candidates.empty or entry_candidates.empty:
            continue
        open_bar_t = open_candidates[0]
        entry_bar_t = entry_candidates[0]
        if entry_bar_t <= open_bar_t:
            continue

        p0 = float(day_df.loc[open_bar_t, "open"])
        p1 = float(day_df.loc[entry_bar_t, "close"])
        if p0 <= 0 or p1 <= 0:
            continue
        r1 = float(np.log(p1 / p0))
        if r1 == 0.0:
            continue
        direction = 1.0 if r1 > 0 else -1.0

        entry_session = day_df.loc[entry_bar_t, "session"]
        session_exit_t = session_exit.get(entry_session)
        if session_exit_t is None or session_exit_t <= entry_bar_t:
            continue

        if exit_after_minutes is None:
            exit_bar_t = session_exit_t
        else:
            target_t = entry_bar_t + pd.Timedelta(minutes=exit_after_minutes)
            window = df.loc[entry_bar_t:session_exit_t]
            fixed_candidates = window.index[window.index >= target_t]
            exit_bar_t = fixed_candidates[0] if not fixed_candidates.empty else session_exit_t
        if exit_bar_t <= entry_bar_t:
            continue
        p_exit = float(df.loc[exit_bar_t, "close"])
        raw_return = float(direction * np.log(p_exit / p1))

        rows.append(
            {
                "session": entry_session,
                "r1": r1,
                "direction": direction,
                "entry_time": entry_bar_t,
                "entry_price": p1,
                "exit_time": exit_bar_t,
                "exit_price": p_exit,
                "raw_return": raw_return,
            }
        )

    return pd.DataFrame(rows)
