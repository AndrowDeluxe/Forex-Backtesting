"""Baustein 3: the Discretized Multiscale Hierarchical Delivery Matrix Psi
(paper Sec 3.3). AD-phase completion is NOT modeled via the paper's
Baum-Welch 4-state HMM (Sec 4.3) - instead this reuses the EMA9/21 crossover
signal already validated in btc_ema_cross/engine.py (crossover = accumu-
lation-to-markup completion, +1; crossunder = markup-to-distribution
completion, -1). Simpler, already-battle-tested, and avoids the over-
engineered-regime-classifier trap this repo has already hit once (see
resources/trend-following-momentum.md's GMM-regime-filter finding: a more
sophisticated classifier fragmented trades and made results worse on a thin
crypto sample)."""

import numpy as np
import pandas as pd


def completion_signal(close: pd.Series, fast: int = 9, slow: int = 21) -> pd.Series:
    """+1 at the bar an EMA(fast)/EMA(slow) crossOVER completes (bullish,
    accumulation-to-markup), -1 at a crossUNDER (bearish, markup-to-
    distribution), 0 elsewhere. Identical EMA construction to btc_ema_cross/
    engine.py::simulate_ema_cross - the same, already-validated signal,
    re-exposed as a signed completion-event series instead of a position
    state machine."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)
    signal = pd.Series(0.0, index=close.index)
    signal[above & ~above_prev] = 1.0
    signal[~above & above_prev] = -1.0
    return signal


def trend_state(close: pd.Series, fast: int = 9, slow: int = 21) -> pd.Series:
    """Binary trend GATE (True = bullish, EMA(fast) > EMA(slow)) - the same
    EMA construction as completion_signal/btc_ema_cross, exposed as a
    continuous STATE instead of an event pulse. Used as a simple HTF
    trend-bias filter on a DIFFERENT strategy (see auction_playbook/
    filters.py::attach_htf_trend_bias) instead of the failed decay-weighted
    Psi aggregation from Phase B - Baustein 3, simplified to the one part
    of it (a directional bias gate) that has a proven analog elsewhere in
    this repo (asian_range_breakout/filters.py's SMA200 trend-bias filter
    for Gold)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast > ema_slow


def psi_matrix(
    htf_completion: pd.Series,
    htf_bar_duration: pd.Timedelta,
    ltf_index: pd.DatetimeIndex,
    liquidity_weight: pd.Series | None = None,
    decay_lambda: float = 0.1,
    lookback_bars: int = 200,
) -> pd.Series:
    """Psi_{s,t} (paper Sec 3.3): exponentially time-decayed sum of the
    NEXT-HIGHER-SCALE's completion signals within a trailing lookback,
    weighted by the liquidity signal-to-noise weight nu_j (Baustein 2),
    reindexed onto the lower-timeframe `ltf_index`.

    No-lookahead note: `auction_playbook.data.fetch_klines` indexes every
    bar by its OPEN time, so a completion "at" that index is only actually
    knowable once the bar CLOSES. The HTF series is shifted forward by one
    `htf_bar_duration` before being forward-filled onto the LTF timeline, so
    an LTF bar formed mid-way through a still-open HTF bar cannot see that
    HTF bar's not-yet-closed signal - same prior-period discipline as
    asian_range_breakout/filters.py's day-lagged joins, at bar-duration
    instead of calendar-day granularity."""
    weight = liquidity_weight.reindex(htf_completion.index).fillna(1.0) if liquidity_weight is not None else 1.0
    weighted = (htf_completion * weight).to_numpy()

    decay_weights = np.exp(-decay_lambda * np.arange(lookback_bars)[::-1])

    def _decayed_sum(window: np.ndarray) -> float:
        w = decay_weights[-len(window):]
        return float(np.dot(window, w))

    psi_htf = pd.Series(weighted, index=htf_completion.index).rolling(lookback_bars, min_periods=1).apply(
        _decayed_sum, raw=True
    )

    psi_known_at = psi_htf.copy()
    psi_known_at.index = psi_known_at.index + htf_bar_duration
    return psi_known_at.reindex(ltf_index, method="ffill")


def rolling_percentile_threshold(series: pd.Series, quantile: float, window: int, min_periods: int | None = None) -> pd.Series:
    """Causal rolling `quantile` of `series` over a trailing `window` (paper
    Sec 5.4: "30-day rolling 70th/30th percentile"). Unlike asian_range_
    breakout.filters.rolling_liquidity_threshold (an EXPANDING window, used
    there because the underlying friction distribution is assumed roughly
    stationary over the whole sample), Psi's own scale can drift with market
    conditions (more/fewer completions per unit time across regimes), so a
    trailing ROLLING window - matching the paper's own choice - is used
    instead of an expanding one."""
    mp = min_periods if min_periods is not None else window // 2
    return series.rolling(window, min_periods=mp).quantile(quantile)
