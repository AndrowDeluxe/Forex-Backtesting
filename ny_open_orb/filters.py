"""Post-hoc entry filters - all take the `entries` DataFrame from
engine.find_entries and return a filtered copy. Composable: chain several
before calling engine.simulate. Direction/weekday/entry-hour need nothing
but `entries` itself; regime-style filters (ADX, RVOL@time, VIX, ADR, EMA
trend bias) go through `filter_by_series` with a per-timestamp lookup
Series/array from ny_open_orb/regime.py or the execution frame.
"""

import numpy as np
import pandas as pd


def filter_by_direction(entries: pd.DataFrame, direction: int) -> pd.DataFrame:
    return entries[entries["direction"] == direction]


def filter_by_weekday(entries: pd.DataFrame, exclude: list[str] | None = None, include_only: list[str] | None = None) -> pd.DataFrame:
    names = entries["entry_time"].dt.day_name()
    if include_only is not None:
        return entries[names.isin(include_only)]
    if exclude is not None:
        return entries[~names.isin(exclude)]
    return entries


def filter_by_entry_hour(entries: pd.DataFrame, start_hour: float, end_hour: float) -> pd.DataFrame:
    """NY-local hour-of-day at entry (entries['entry_time'] is already
    tz-aware America/New_York, from the execution frame's index)."""
    hour = entries["entry_time"].dt.hour + entries["entry_time"].dt.minute / 60.0
    return entries[(hour >= start_hour) & (hour < end_hour)]


def values_at(entries: pd.DataFrame, lookup: pd.Series) -> np.ndarray:
    """Looks up `lookup` (indexed by bar timestamp OR by session/NY-midnight
    date, e.g. from regime.py) at each entry's time/session - tries an exact
    timestamp reindex first (bar-level series like frame['adx']), falls back
    to session-date reindex (daily-resolution regime series)."""
    by_time = lookup.reindex(entries["entry_time"])
    if by_time.notna().any() or "session" not in entries.columns:
        return by_time.to_numpy()
    return lookup.reindex(entries["session"]).to_numpy()


def filter_by_series(entries: pd.DataFrame, values: np.ndarray, min_value: float | None = None, max_value: float | None = None) -> pd.DataFrame:
    mask = np.ones(len(entries), dtype=bool)
    if min_value is not None:
        mask &= values >= min_value
    if max_value is not None:
        mask &= values <= max_value
    return entries[mask]


def filter_by_category(entries: pd.DataFrame, values: np.ndarray, allowed: tuple) -> pd.DataFrame:
    """Like filter_by_series but for a categorical lookup (e.g. regime.py's
    'high_vix'/'low_vix' labels or an EMA-ribbon bias of +1/-1/0)."""
    return entries[np.isin(values, allowed)]
