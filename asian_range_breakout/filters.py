"""Post-hoc filters for asian_range_breakout trades (ADX regime, VIX regime) -
applied to an already-simulated trades DataFrame, same pattern as
orb_strategy.py::apply_orb_filters. Dropping a trade here is equivalent to
never having entered it - each Asian-range window is an independent event,
so filtering doesn't need to re-run the simulation."""

import pandas as pd


def apply_adx_filter(
    trades: pd.DataFrame, adx_min: float | None = None, adx_max: float | None = None
) -> pd.DataFrame:
    if trades.empty or (adx_min is None and adx_max is None):
        return trades
    mask = pd.Series(True, index=trades.index)
    if adx_min is not None:
        mask &= trades["adx_at_entry"] >= adx_min
    if adx_max is not None:
        mask &= trades["adx_at_entry"] <= adx_max
    return trades[mask]


def attach_vix(trades: pd.DataFrame, vix_daily: pd.Series) -> pd.DataFrame:
    """Attaches the most recent PRIOR trading day's VIX close (strictly
    before the entry's calendar date) to each trade - entries happen
    01:00-11:00 NY, always before that same day's 16:00 ET VIX print, so
    using that day's own close would be lookahead. ffill via searchsorted,
    not a plain date-equality join, so weekends/holidays (no VIX print)
    correctly carry the last known prior value forward."""

    if trades.empty:
        return trades.assign(vix_at_entry=pd.Series(dtype=float))

    out = trades.copy()
    entry_dates = out["entry_time"].dt.tz_localize(None).dt.normalize()
    vix_sorted = vix_daily.sort_index()

    idx = vix_sorted.index.searchsorted(entry_dates.to_numpy(), side="left") - 1
    idx_clipped = idx.clip(min=0)
    values = vix_sorted.to_numpy()[idx_clipped]
    values = pd.Series(values, index=out.index, dtype=float)
    values[idx < 0] = float("nan")  # entry predates all available VIX data
    out["vix_at_entry"] = values
    return out


def apply_vix_filter(
    trades: pd.DataFrame, vix_min: float | None = None, vix_max: float | None = None
) -> pd.DataFrame:
    if trades.empty or (vix_min is None and vix_max is None):
        return trades
    mask = pd.Series(True, index=trades.index)
    if vix_min is not None:
        mask &= trades["vix_at_entry"] >= vix_min
    if vix_max is not None:
        mask &= trades["vix_at_entry"] <= vix_max
    return trades[mask]
