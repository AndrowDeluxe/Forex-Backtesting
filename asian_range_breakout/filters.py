"""Post-hoc filters for asian_range_breakout trades (ADX regime, VIX regime) -
applied to an already-simulated trades DataFrame, same pattern as
orb_strategy.py::apply_orb_filters. Dropping a trade here is equivalent to
never having entered it - each Asian-range window is an independent event,
so filtering doesn't need to re-run the simulation."""

import numpy as np
import pandas as pd

from strategy.indicators import compute_atr


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


def attach_entry_delay(trades: pd.DataFrame) -> pd.DataFrame:
    """Attaches `delay_bars`: how many M15 bars passed between the Asian
    range closing (window_end) and the breakout order actually filling
    (entry_time). NOT lookahead - equivalent to "cancel the resting order if
    unfilled after N bars", fully knowable in real time (bottleneck
    diagnosis, 2026-08-08: fast fills are consistently higher-quality than
    slow ones - see scripts/research_gold_bottleneck_diagnosis.py)."""
    out = trades.copy()
    out["delay_bars"] = ((out["entry_time"] - out["window_end"]).dt.total_seconds() / 900).round().astype(int)
    return out


def apply_entry_delay_filter(trades: pd.DataFrame, max_delay_bars: int = 3) -> pd.DataFrame:
    """Drops trades whose breakout order took longer than max_delay_bars
    M15 bars to fill (see attach_entry_delay)."""
    out = attach_entry_delay(trades)
    return out[out["delay_bars"] <= max_delay_bars]


def attach_pre_window_momentum(
    trades: pd.DataFrame, df: pd.DataFrame, lookback_bars: int = 8, atr_n: int = 14
) -> pd.DataFrame:
    """Attaches `momentum_r`: Gold's own ATR-normalized net directional move
    over the `lookback_bars` M15 bars immediately BEFORE the Asian range
    closes (window_end) - "was there already real directional thrust heading
    into the session, or was price just drifting/chopping". Fully known at
    window_end, no lookahead (unlike a same-bar breakout-strength measure,
    which isn't knowable until the fill bar closes - see engine.py's
    entry_mode="close" dead end). Different timescale/signal than both the
    SMA200 trend-bias filter (multi-month) and ADX-at-entry (smoothed trend
    strength, measured the same moment but a different construction) -
    momentum_r is a raw, short-horizon impulse measure.
    `momentum_r` sign follows price direction (positive = up-move); use
    together with the trade's own `direction` to test alignment, or take
    `.abs()` to test raw thrust magnitude regardless of direction."""
    atr = compute_atr(df, n=atr_n)
    close = df["close"]
    pos = df.index.get_indexer(trades["window_end"])
    valid = pos >= lookback_bars  # need lookback_bars of history before window_end

    momentum = np.full(len(trades), np.nan)
    atr_at_window = np.full(len(trades), np.nan)
    valid_pos = pos[valid]
    momentum[valid] = close.to_numpy()[valid_pos] - close.to_numpy()[valid_pos - lookback_bars]
    atr_at_window[valid] = atr.to_numpy()[valid_pos]

    out = trades.copy()
    with np.errstate(invalid="ignore", divide="ignore"):
        out["momentum_r"] = momentum / atr_at_window
    return out.dropna(subset=["momentum_r"])


def attach_silver_alignment(trades: pd.DataFrame, daily_close_silver: pd.Series, window: int = 5) -> pd.DataFrame:
    """Attaches an `aligned` boolean column: True if the trade's direction
    matches Silver's own recent price direction (long while Silver has been
    rising over `window` days, short while falling) - a cross-asset
    momentum-confirmation filter extracted from the Gold-Silver-BTC lead-lag
    paper (paper151-style distillation, 2026-08-08 - see
    app_pages/goldi_papers_202608.py tab 3). Structurally identical to
    attach_trend_bias, just Silver's short-term change instead of Gold's own
    SMA200. Drops trades that predate `window` days of Silver history."""
    out = attach_series_change(trades, daily_close_silver, "silver_chg", window=window)
    out = out.dropna(subset=["silver_chg"])
    is_long = out["direction"] == "long"
    out["aligned"] = (is_long & (out["silver_chg"] > 0)) | (~is_long & (out["silver_chg"] < 0))
    return out


def apply_silver_alignment_filter(trades: pd.DataFrame, daily_close_silver: pd.Series, window: int = 5) -> pd.DataFrame:
    """Drops trades where the breakout direction disagrees with Silver's own
    recent price direction (see attach_silver_alignment)."""
    out = attach_silver_alignment(trades, daily_close_silver, window=window)
    return out[out["aligned"]]


def attach_cot_sentiment(trades: pd.DataFrame, sentiment_series: pd.Series, colname: str = "cot_si") -> pd.DataFrame:
    """Attaches a CFTC COT sentiment index (Wang 2001, see cot.py) to each
    trade - `sentiment_series` must already be indexed by PUBLICATION date
    (not report date, see cot.py's 3-day lag shift) so this is a plain
    no-lookahead prior-value join, same as attach_vix/attach_dxy."""
    return _attach_prior_day_series(trades, sentiment_series, colname)


def apply_momentum_alignment_filter(
    trades: pd.DataFrame, df: pd.DataFrame, lookback_bars: int = 8, atr_n: int = 14
) -> pd.DataFrame:
    """Keeps only trades where the breakout direction matches the pre-window
    momentum direction (long after an up-thrust into the session, short
    after a down-thrust) - see attach_pre_window_momentum."""
    out = attach_pre_window_momentum(trades, df, lookback_bars=lookback_bars, atr_n=atr_n)
    is_long = out["direction"] == "long"
    aligned = (is_long & (out["momentum_r"] > 0)) | (~is_long & (out["momentum_r"] < 0))
    return out[aligned]


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
