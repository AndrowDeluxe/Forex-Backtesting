"""Substitute momentum signal for the JPM spillover paper's own
(proprietary, undisclosed - referenced there only as coming from a
different paper, "Designing robust trend-following system") formula. The
paper describes its own signal in these words: "equivalent to conducting
the statistical hypothesis tests on the mean return of assets over
certain look-backs... the values fall within the range of [-1, 1]". This
implements literally that description: a one-sample t-test on the mean
daily log return over the lookback window, mapped through the standard
normal CDF onto [-1, 1] (2*Phi(t)-1, so t=0 -> 0, large positive t -> +1,
large negative t -> -1) - a reasonable, paper-consistent SUBSTITUTE, not a
reproduction of JPM's actual formula. See knowledge/resources/
cross-asset-momentum-spillover.md for the full disclosure."""

import numpy as np
import pandas as pd
from scipy.stats import norm

LOOKBACKS = [32, 64, 126, 252, 504]


def momentum_signal(close: pd.Series, lookback: int) -> pd.Series:
    """2*Phi(t_stat)-1 of the mean daily log return over a trailing
    `lookback`-day window, computed at every bar using only data up to and
    including that bar (no lookahead). NaN for the first `lookback` bars."""
    log_ret = np.log(close / close.shift(1))
    mean = log_ret.rolling(lookback).mean()
    std = log_ret.rolling(lookback).std(ddof=1)
    t_stat = mean / (std / np.sqrt(lookback))
    return pd.Series(2 * norm.cdf(t_stat) - 1, index=close.index, name=f"mom_{lookback}")


def all_momentum_signals(closes: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """closes: DataFrame (date x pair). Returns {lookback: DataFrame(date x
    pair)} of momentum_signal values, one DataFrame per lookback."""
    out = {}
    for lb in LOOKBACKS:
        out[lb] = pd.DataFrame({pair: momentum_signal(closes[pair], lb) for pair in closes.columns})
    return out
