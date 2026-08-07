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


def _attach_prior_day_series(trades: pd.DataFrame, daily_series: pd.Series, colname: str) -> pd.DataFrame:
    """Attaches the most recent PRIOR trading day's value of daily_series
    (strictly before the entry's calendar date) to each trade - entries
    happen 01:00-11:00 NY, always before that same day's close print, so
    using that day's own value would be lookahead. ffill via searchsorted,
    not a plain date-equality join, so weekends/holidays (no print) correctly
    carry the last known prior value forward. Shared by attach_vix/attach_dxy/
    attach_series_change - same alignment logic regardless of source series."""

    if trades.empty:
        return trades.assign(**{colname: pd.Series(dtype=float)})

    out = trades.copy()
    entry_dates = out["entry_time"].dt.tz_localize(None).dt.normalize()
    s_sorted = daily_series.dropna().sort_index()

    idx = s_sorted.index.searchsorted(entry_dates.to_numpy(), side="left") - 1
    idx_clipped = idx.clip(min=0)
    values = s_sorted.to_numpy()[idx_clipped]
    values = pd.Series(values, index=out.index, dtype=float)
    values[idx < 0] = float("nan")  # entry predates all available data for this series
    out[colname] = values
    return out


def attach_vix(trades: pd.DataFrame, vix_daily: pd.Series) -> pd.DataFrame:
    return _attach_prior_day_series(trades, vix_daily, "vix_at_entry")


def attach_dxy(trades: pd.DataFrame, dxy_daily: pd.Series) -> pd.DataFrame:
    """Attaches the prior trading day's US Dollar Index (DXY) close - context
    signal for the "151 Trading Strategies" cross-asset-confirmation idea
    (Gold is USD-denominated; a trending dollar is a structural head-/
    tailwind independent of Gold's own chart)."""
    return _attach_prior_day_series(trades, dxy_daily, "dxy_at_entry")


def attach_series_change(
    trades: pd.DataFrame, daily_series: pd.Series, colname: str, window: int = 5
) -> pd.DataFrame:
    """Attaches the prior trading day's window-day percent change of
    daily_series (e.g. VIX or DXY momentum instead of level) to each trade -
    same no-lookahead alignment as attach_vix/attach_dxy."""
    change = daily_series.sort_index().pct_change(window) * 100
    return _attach_prior_day_series(trades, change, colname)


def attach_series_level(trades: pd.DataFrame, daily_series: pd.Series, colname: str) -> pd.DataFrame:
    """Generic level attachment (any daily series, any column name) - same
    no-lookahead alignment as attach_vix/attach_dxy, without a fixed column
    name. Used e.g. for Gold's own daily close/SMA (time-series-momentum
    trend-bias filter)."""
    return _attach_prior_day_series(trades, daily_series, colname)


def attach_trend_bias(trades: pd.DataFrame, daily_close: pd.Series, sma_window: int = 200) -> pd.DataFrame:
    """Attaches a `aligned` boolean column: True if the trade's direction
    matches Gold's own prevailing daily trend (long while the prior day's
    close was above its own SMA, short while below) - the "151 Trading
    Strategies" time-series-momentum building block (chapter 10.4) used as a
    directional bias on top of the Asian-Range Breakout, instead of as its
    own standalone strategy (see triple_ma for that). Drops trades that
    predate `sma_window` days of history (no SMA value yet available)."""
    sma = daily_close.rolling(sma_window).mean()
    out = attach_series_level(trades, daily_close, "gold_close_prior")
    out = attach_series_level(out, sma, "gold_sma_prior")
    out = out.dropna(subset=["gold_close_prior", "gold_sma_prior"])
    bias_up = out["gold_close_prior"] > out["gold_sma_prior"]
    is_long = out["direction"] == "long"
    out["aligned"] = (is_long & bias_up) | (~is_long & ~bias_up)
    return out


def apply_trend_bias_filter(trades: pd.DataFrame, daily_close: pd.Series, sma_window: int = 200) -> pd.DataFrame:
    """Drops counter-trend trades (see attach_trend_bias)."""
    out = attach_trend_bias(trades, daily_close, sma_window=sma_window)
    return out[out["aligned"]]


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
