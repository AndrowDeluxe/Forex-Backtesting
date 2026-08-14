"""Post-hoc filters for already-simulated mt5_trend_pullback trades - same
pattern as asian_range_breakout/filters.py (dropping a trade here is
equivalent to never having entered it, since each signal is an independent
event). Promoted out of scripts/research_mt5_trend_pullback_proven_filters.py
so app_pages/mt5_trend_pullback.py and future scripts can share one
implementation instead of copies drifting apart.
"""

import numpy as np
import pandas as pd

ALIGNMENT_WINDOW = 5  # unchanged from the validated ASB setting (attach_silver_alignment)


def alignment_filter(trades: pd.DataFrame, partner_close_d1: pd.Series, window: int = ALIGNMENT_WINDOW) -> pd.DataFrame:
    """Long-only adaptation of asian_range_breakout.filters.attach_silver_alignment
    (that module's `direction` column is the string "long"/"short"; this
    strategy's trades use the int convention from strategy.backtest, and is
    long-only anyway, so the alignment test collapses to a single condition):
    keep a trade only if the confirming asset's own `window`-day close change,
    as of the entry's calendar date (last value strictly BEFORE entry - no
    lookahead, same searchsorted convention as
    asian_range_breakout.filters._attach_prior_day_series), was positive.

    2026-08-14 finding (scripts/research_mt5_trend_pullback_proven_filters.py):
    Gold-confirms-Silver clearly helps Silver on its own (new-regime OOS PF
    1.347->1.530, Sharpe 0.47->0.65); Silver-confirms-Gold and Gold-confirms-
    Platinum were roughly neutral/negative - NOT applied elsewhere."""
    if trades.empty:
        return trades
    chg = partner_close_d1.sort_index().pct_change(window)
    entry_dates = trades["entry_time"].dt.tz_localize(None).dt.normalize()
    s_sorted = chg.dropna().sort_index()
    idx = s_sorted.index.searchsorted(entry_dates.to_numpy(), side="left") - 1
    idx_clipped = idx.clip(min=0)
    values = s_sorted.to_numpy()[idx_clipped]
    values = pd.Series(values, index=trades.index, dtype=float)
    values[idx < 0] = np.nan
    out = trades.copy()
    out["partner_chg"] = values
    out = out.dropna(subset=["partner_chg"])
    return out[out["partner_chg"] > 0]
