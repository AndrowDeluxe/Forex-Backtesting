"""Day-level regime signals, each returned as a Series indexed by session
date (NY-local midnight) for use with filters.filter_by_series(entries,
filters.values_at(entries, series)). All are computed with a strict
`.shift(1)`-then-asof join so only a PRIOR day's fully-closed value can ever
reach a given session - no lookahead, matching the day_atr/vol_regime
convention already used by orb_strategy/pipeline.py.
"""

import numpy as np
import pandas as pd

from strategy.mtf_ema_ribbon import attach_mtf_ema_ribbon, ribbon_bias


def _asof_prior(session_dates: pd.DatetimeIndex, daily_series: pd.Series) -> pd.Series:
    """Maps each session date to the latest daily_series value from a
    STRICTLY earlier date (shift(1) before the asof join, so even if the
    two indices' calendar-date labels are off by a day - e.g. a UTC-stamped
    daily bar re-labelled after tz_convert - the result is still guaranteed
    non-lookahead: always "the previous available reading", never today's)."""
    shifted = daily_series.sort_index().shift(1).rename("value")
    shifted.index.name = "_ts"
    right = shifted.reset_index()
    unique_sessions = pd.DatetimeIndex(session_dates).unique().sort_values()
    left = pd.DataFrame({"session": unique_sessions})
    merged = pd.merge_asof(left, right.sort_values("_ts"), left_on="session", right_on="_ts", direction="backward")
    return pd.Series(merged["value"].to_numpy(), index=merged["session"])


def vix_regime(session_dates: pd.DatetimeIndex, vix_daily: pd.Series, median_window: int = 60) -> pd.DataFrame:
    """Prior day's VIX close + a high/low label split at VIX's OWN trailing
    rolling median (relative regime, not an arbitrary fixed level - VIX's
    baseline has drifted across 2016-2026)."""
    vix_level = _asof_prior(session_dates, vix_daily)
    vix_median = vix_level.rolling(median_window, min_periods=median_window // 2).median()
    regime = pd.Series(np.where(vix_level > vix_median, "high_vix", "low_vix"), index=vix_level.index, dtype=object)
    regime[vix_level.isna() | vix_median.isna()] = None
    return pd.DataFrame({"vix": vix_level, "vix_median": vix_median, "vix_regime": regime})


def average_daily_range(m15: pd.DataFrame, n: int = 20) -> pd.Series:
    """ADR(n): simple trailing average of daily high-low range (distinct
    from Wilder's ATR, which also folds in gap-through-prior-close) - the
    plain "average daily range in points" day-traders commonly reference.
    Shifted so a day's own range never feeds its own reading."""
    daily = m15.resample("1D").agg(high=("high", "max"), low=("low", "min")).dropna()
    daily_range = daily["high"] - daily["low"]
    return daily_range.shift(1).rolling(n, min_periods=n // 2).mean()


def orb_width_percentile(session_width: pd.Series, n: int = 60) -> pd.Series:
    """Percentile rank (0.0 = narrowest, 1.0 = widest) of each session's OWN
    opening-range width against the trailing n sessions, INCLUDING itself -
    not the shift(1)-before-rolling convention used elsewhere in this file,
    because a session's own width is already fully known (range has closed)
    by the time any entry can fire, per range.py's range_end gate - no
    lookahead either way. NaN until n/2 sessions of history exist.

    Input: a session-indexed width series, e.g.
    `frame.groupby("session")["orb_width"].first()` from engine.build_frame's
    output (frame already carries orb_width per bar, broadcast from
    range.compute_session_range).

    Motivated by the NQ-futures ORB-Width setup-quality filter in
    knowledge/resources/opening-range-breakout.md (narrow opening range ->
    less pre-open participant disagreement -> stronger directional signal on
    the subsequent breakout) - here as a walk-forward-safe ROLLING percentile
    rather than that paper's single static IS-calibrated threshold, which its
    own OOS section showed collapses when the underlying width distribution
    shifts (IS mean 53.5pt -> OOS mean 74.7pt, +40%)."""
    min_hist = max(n // 2, 1)

    def _rank(window: np.ndarray) -> float:
        history, today = window[:-1], window[-1]
        history = history[~np.isnan(history)]
        if len(history) < min_hist - 1 or np.isnan(today):
            return np.nan
        return float((history <= today).mean())

    return session_width.rolling(n, min_periods=min_hist).apply(_rank, raw=True)


def ema_trend_bias(m15: pd.DataFrame, session_dates: pd.DatetimeIndex) -> pd.Series:
    """+1/-1/0 daily HTF-EMA-ribbon bias (strategy/mtf_ema_ribbon.py, the
    user-supplied 4H-50/1D-50/1W-50/1D-200 stack), evaluated once per
    session from the PRIOR day's ribbon reading (asof, no lookahead) -
    "was price trending up/down going into today's open"."""
    ribboned = attach_mtf_ema_ribbon(m15)
    bias = ribbon_bias(ribboned)
    daily_bias = bias.resample("1D").last().dropna()
    return _asof_prior(session_dates, daily_bias)
