"""Market-regime clustering via Gaussian Mixture Models (GMM), per the
paper's Sec. 3.4.1: the paper motivates GMM over k-means by observing that
its stationarised return series (logged first difference) looks
approximately Gaussian, then fits a 4-component GMM to find regimes.

Two things the paper does NOT specify precisely, filled in here with an
explicit, documented choice rather than silently guessed:

1. **Which features feed the GMM.** The paper only says it used "12 months
   moving average volatility" alongside the return series. We use the log
   return itself plus its rolling realised volatility (`vol_window`,
   default 21 trading days ~= 1 month) as the two GMM features. A literal
   12-month (252-day) rolling window was tried and rejected: it barely
   moves day to day, which defeats the purpose of a regime *switch*
   detector - the paper's own regime plot (Fig. 7) clearly shows the
   market moving between clusters over horizons much shorter than 12
   months (e.g. within 2008-2009).
2. **Cluster naming.** The paper labels its 4 clusters "Breakout",
   "Frenzy/high volatility", "Sideways/low volatility", "Disbelief" purely
   by eyeballing a return-vs-volatility scatter plot after the fact,
   with no stated objective rule. Reproducing that specific subjective
   labeling isn't falsifiable, so this module only orders clusters by
   their mean realised volatility (low -> high) and leaves the
   "Breakout"/"Frenzy" style storytelling to the dashboard's prose, not
   to the code.
"""

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

N_REGIMES_DEFAULT = 4
VOL_WINDOW_DEFAULT = 21
RANDOM_STATE = 42


def compute_regimes(
    close: pd.Series, n_regimes: int = N_REGIMES_DEFAULT,
    vol_window: int = VOL_WINDOW_DEFAULT, random_state: int = RANDOM_STATE,
) -> pd.Series:
    """Returns an integer regime label per bar (0 = lowest mean realised
    volatility cluster, ... n_regimes-1 = highest), reindexed to `close`'s
    full index with NaN for bars before the rolling-vol warmup completes.
    """
    log_ret = np.log(close).diff()
    vol = log_ret.rolling(vol_window).std()
    features = pd.concat([log_ret, vol], axis=1)
    features.columns = ["log_ret", "vol"]
    features = features.dropna()

    if len(features) < n_regimes * 10:
        raise ValueError("not enough data after warmup to fit GMM regimes")

    gmm = GaussianMixture(n_components=n_regimes, random_state=random_state, n_init=4)
    raw_labels = gmm.fit_predict(features.values)

    vol_by_cluster = pd.Series(features["vol"].values).groupby(raw_labels).mean()
    order = vol_by_cluster.sort_values().index.tolist()
    remap = {old: new for new, old in enumerate(order)}
    labels = pd.Series([remap[label] for label in raw_labels], index=features.index, name="regime")

    return labels.reindex(close.index)


REGIME_LABELS = {
    0: "Regime 0 (niedrigste Vola)",
    1: "Regime 1",
    2: "Regime 2",
    3: "Regime 3 (höchste Vola)",
}
