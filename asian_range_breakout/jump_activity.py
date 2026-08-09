"""Generic jump-activity (bipower-variation) regime measure for Gold M15
data - NOT a literal replication of any specific paper (the "Hizmeri et al."
jump-activity idea flagged in an earlier session isn't available in this
repo/session to implement faithfully). This is the standard Barndorff-
Nielsen & Shephard-style realized-variance/bipower-variation jump
decomposition, used here purely as a volatility-REGIME measure ("how much of
a day's variance came from a few large jumps vs. smooth diffusion"), serving
the same purpose the flagged idea was meant to test.

RV (realized variance) = sum of squared M15 log-returns for the day.
BV (bipower variation) = (pi/2) x sum of |r_i| x |r_{i-1}| - a jump-robust
variance estimator (large single-bar jumps don't inflate it the way they
inflate RV, since it needs TWO consecutive large returns to move much).
Jump ratio RJ = max(0, RV - BV) / RV in [0, 1] - near 0 on smooth/diffusive
days, higher on days where a few isolated jumps dominated the variance."""

import numpy as np
import pandas as pd


def compute_daily_jump_ratio(df: pd.DataFrame) -> pd.Series:
    """One value per calendar day of df's own index (NY local for Gold M15,
    see asian_range_breakout/data.py): RJ = (RV - BV) / RV."""
    r = np.log(df["close"]).diff()
    day = df.index.date
    rows = []
    for d, idx in pd.Series(r.index, index=day).groupby(level=0):
        ret = r.loc[idx].dropna()
        if len(ret) < 5:
            continue
        rv = (ret ** 2).sum()
        bv = (np.pi / 2) * (ret.abs().to_numpy()[1:] * ret.abs().to_numpy()[:-1]).sum()
        rj = max(0.0, (rv - bv) / rv) if rv > 0 else np.nan
        rows.append({"date": pd.Timestamp(d), "jump_ratio": rj})
    return pd.DataFrame(rows).set_index("date")["jump_ratio"]
