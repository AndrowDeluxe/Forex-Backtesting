"""Corwin & Schultz (2012) bid-ask-spread estimator from daily high/low
prices only - Yildirim SSRN 6353258, Appendix A, equations (4)-(7). Runs on
the FX D1 OHLC already cached by combined_strategy.data (the 6 pairs
matching this project's 6 non-US countries), so Layer 3 needs no new data
source, unlike Layer 1 (fred.py)."""

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe

_K = 3 - 2 * np.sqrt(2)


def corwin_schultz_spread(high: pd.Series, low: pd.Series) -> pd.Series:
    """Daily effective proportional bid-ask spread S_HL,t, indexed like
    `high`/`low` (value at index t uses the two-day window [t, t+1], so it
    is assigned to date t - the paper's own convention, eq. 4-7)."""
    h2 = pd.concat([high, high.shift(-1)], axis=1).max(axis=1)
    l2 = pd.concat([low, low.shift(-1)], axis=1).min(axis=1)
    gamma = np.log(h2 / l2) ** 2

    beta = (np.log(high / low) + np.log(high.shift(-1) / low.shift(-1))) ** 2

    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)
    spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    # negative alpha (near-zero true spread, noise-dominated) is a known
    # artefact of the estimator - the paper does not truncate it, so neither
    # do we, but it is worth knowing it can go slightly negative.
    return spread.rename("cs_spread")


def fetch_fx_friction(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.Series:
    df = fetch_timeframe(pair, "D1", start, end, force_refresh=force_refresh)
    s = corwin_schultz_spread(df["High"], df["Low"])
    # Dukascopy D1 index is tz-aware (UTC); the rest of this package (FRED
    # yields, the daily calendar grid) is tz-naive - normalize here so
    # downstream reindex()/align calls don't silently produce all-NaN.
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s
