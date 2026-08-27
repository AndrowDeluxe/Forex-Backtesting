"""Baustein 2: liquidity-vacuum PROXY, not a replication. The FLPD paper's
Temporal Liquidity Vacuum (Def. 1, Sec 3.1) needs order-book depth at every
price level - this repo's crypto data (auction_playbook.data.fetch_klines)
has OHLCV + taker buy/sell volume + n_trades, but no book depth. Two
independently-derived, genuinely-available signals stand in instead:

1. Trade-count thinness - genuine data (n_trades is real, not estimated),
   just a coarser liquidity signal than book depth.
2. Corwin-Schultz spread widening - a well-established ESTIMATOR from
   High/Low alone, reused unchanged from bond_yield_indicator.friction
   (generic to any High/Low series, not FX-specific).

The TLV duration/power-law claim (Theorem 1a) is NOT attempted here - a
proxy cannot honestly stand in for a claim that is specifically about
order-book depth dynamics. See resources/crypto-hurst-wyckoff-cycles.md."""

import numpy as np
import pandas as pd

from bond_yield_indicator.friction import corwin_schultz_spread


def _rolling_percentile_rank(s: pd.Series, window: int) -> pd.Series:
    """Causal rolling percentile rank of each value within its own trailing
    `window` (fraction of the trailing window at or below the current bar's
    value) - each bar only ever compares itself against bars up to and
    including itself, no look-ahead."""
    return s.rolling(window, min_periods=window // 2).apply(lambda w: (w <= w[-1]).mean(), raw=True)


def trade_count_thinness(n_trades: pd.Series, window: int = 30 * 24) -> pd.Series:
    """LOW percentile = unusually few trades vs. this pair's own recent
    baseline (default window: 30 days on 1h bars) - the closest genuine-data
    analog to a liquidity vacuum this data budget allows."""
    return _rolling_percentile_rank(n_trades, window)


def spread_widening(high: pd.Series, low: pd.Series, window: int = 30 * 24) -> pd.Series:
    """HIGH percentile = wider estimated Corwin-Schultz spread vs. this
    pair's own recent baseline = worse estimated liquidity.

    `corwin_schultz_spread` itself uses a [t, t+1] two-bar window per the
    estimator's own construction (see bond_yield_indicator/friction.py's
    docstring) - the value nominally indexed at bar t is only actually
    known once bar t+1 has closed. Shifted here by one extra bar so the
    returned series is genuinely causal (known-at-bar-t), the same
    discipline asian_range_breakout/filters.py applies by always using the
    PRIOR day's friction value rather than the same-day one."""
    cs = corwin_schultz_spread(high, low).shift(1)
    return _rolling_percentile_rank(cs, window)


def liquidity_weight(n_trades: pd.Series, high: pd.Series, low: pd.Series, window: int = 30 * 24) -> pd.Series:
    """Combined nu_j in [0, 1] (paper Sec 3.3's signal-to-noise weight):
    average of (1 - thinness_percentile) and (1 - spread_percentile) - high
    weight when trading activity is normal-to-high AND the estimated spread
    is normal-to-tight (trust the completion signal more), low weight during
    a proxy-flagged liquidity vacuum (both trading is thin AND the estimated
    spread is wide) - matches the paper's own intent for nu_j."""
    thin = trade_count_thinness(n_trades, window=window)
    wide = spread_widening(high, low, window=window)
    weight = ((1 - thin) + (1 - wide)) / 2
    return weight.fillna(1.0)  # no baseline yet -> assume full trust (matches nu_j's max value of 1)
