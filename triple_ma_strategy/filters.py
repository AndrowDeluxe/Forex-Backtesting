"""Post-hoc regime filter on top of the position signal from signals.py.

Empirically tested, not assumed - and the honest result is a **negative
one**: neither variant implemented here robustly improves the strategy,
on any of SP500/NASDAQ/GOLD (Single-TEMA n=252, full method + numbers in
MEMORY / the dashboard's honest banner). Two variants were tried because
the first one's failure had an identifiable, fixable-looking cause that
turned out not to actually fix anything:

1. **Continuous filter** (`apply_regime_filter`): force flat on every bar
   whose regime is in `exclude_regimes`, regardless of whether a trade is
   already open. This *hurts* on every instrument tested (e.g. SP500
   profit factor 2.67 -> 0.98 excluding only the thinnest, worst-looking
   cluster) - because regime labels flip far more often (bar by bar) than
   trades are held (average 17-40 days), so a mid-trade regime flip
   forces an exit and fragments what would have been one long winning
   trade into several smaller ones. Same underlying mechanism as this
   repo's TP/breakeven findings elsewhere (asian_range_breakout): the
   edge here lives in letting a trade run uninterrupted, and any rule
   that can force an early exit - for any reason - cuts into exactly that.
2. **Entry-only gate** (`apply_entry_regime_filter`): only block *new*
   entries during an excluded regime, never force an exit once already in
   a trade. This avoids the fragmentation problem (trade count is
   basically unchanged when excluding the already-rarely-entered regimes
   1/3), but restricting entries to only the best-looking cluster (regime
   2) still doesn't produce a consistent improvement - profit factor
   moves in different directions per instrument, Sharpe and alpha get
   worse on 2 of 3 tested instruments. The regime/entry-quality
   correlation seen when just slicing existing trades by entry regime
   (regime 2 trades individually look better) does not survive turning
   it into an actual entry rule - the same "looked good until you try to
   trade it" pattern already seen with checklist_strategy's ADX/VIX/
   best-hours filters.

Both are kept here (exposed as an explicit, off-by-default dashboard
toggle) as a documented negative result, not deleted - the point is to
show the filter was tried honestly, not to hide that it didn't work.
"""

import pandas as pd


def apply_regime_filter(position: pd.Series, regimes: pd.Series, exclude_regimes: set[int]) -> pd.Series:
    """Zeroes out `position` on bars whose regime label is in
    `exclude_regimes`. Uses the regime value at the same bar as the
    signal itself (both are computed from information available through
    that bar's close), so no extra lookahead is introduced beyond what
    `signals.py` already has.
    """
    if not exclude_regimes:
        return position
    filtered = position.copy()
    excluded_mask = regimes.reindex(position.index).isin(exclude_regimes)
    filtered[excluded_mask.fillna(False)] = 0.0
    return filtered


def apply_entry_regime_filter(position: pd.Series, regimes: pd.Series, exclude_regimes: set[int]) -> pd.Series:
    """Like `apply_regime_filter`, but only blocks the *opening* bar of a
    new position - once a trade is open it is never force-closed by a
    regime change, avoiding the mid-trade fragmentation problem.
    """
    if not exclude_regimes:
        return position
    allowed_entry = ~regimes.reindex(position.index).isin(exclude_regimes)
    allowed_entry = allowed_entry.fillna(True)

    result = pd.Series(0.0, index=position.index)
    in_pos = False
    for ts, sig in position.items():
        if sig == 1.0:
            if in_pos or allowed_entry.loc[ts]:
                result.loc[ts] = 1.0
                in_pos = True
            else:
                result.loc[ts] = 0.0
        else:
            result.loc[ts] = 0.0
            in_pos = False
    return result
