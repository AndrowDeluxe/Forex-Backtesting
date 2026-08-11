"""Rates-Ampel (grün/gelb/rot) - the source playbook's "Rates" filter,
quantified against the best freely available intraday proxy: BUND vs.
USTBOND CFD price action over the Settle window (06:00-09:00 Berlin, same
window as strategy/cls_advanced.py). Disclosed substitution: this is a
LONG-END duration/term-premium signal (~10y Bund, ~15-25y UST future), not
the front-end/2y relative-rate-expectations signal the source material
describes ("Front End Rates oder kurze Zinserwartungen") - no free source
gives that at intraday resolution for both EUR and USD (checked 2026-08-11:
neither Dukascopy nor yfinance lists a EUR front-end/2y intraday feed).
Treat any "grün"/"rot" read below as a long-end proxy read, not a literal
2y-yield-spread read.

Sign convention: a bond's PRICE moves inversely to its yield. "EUR rates
strengthen" (page 6 of the source deck) means EUR yields rise, i.e. Bund
price FALLS. "USD rates weaken" means UST yields fall, i.e. UST price
RISES. Both support EUR/USD LONG. So:

    rate_support_score = ustbond_return - bund_return

is positive when USTBOND outperforms BUND in price (USD yields falling
relative to EUR yields) -> supports EUR/USD long; negative -> supports
EUR/USD short.
"""

import numpy as np
import pandas as pd

from strategy.cls_advanced import ASIA_END, SETTLE_END, to_berlin


def compute_rate_support_score(bund: pd.DataFrame, ustbond: pd.DataFrame) -> pd.Series:
    """Per Berlin calendar day: rate_support_score over the Settle window
    (06:00-09:00), see module docstring for sign convention. NaN on days
    where either instrument has no bars in the window (e.g. CFD-specific
    holiday gaps)."""
    rows = {}
    for label, df in (("bund", bund), ("ustbond", ustbond)):
        berlin = to_berlin(df.index)
        hour = berlin.hour + berlin.minute / 60.0
        date = pd.Series(berlin.date, index=df.index)
        d = pd.DataFrame({"date": date, "hour": hour, "close": df["close"].to_numpy(), "open": df["open"].to_numpy()})
        settle = d[(d["hour"] >= ASIA_END) & (d["hour"] < SETTLE_END)]
        by_day = settle.groupby("date").agg(open_=("open", "first"), close_=("close", "last"))
        ret = (by_day["close_"] / by_day["open_"] - 1).rename(label)
        rows[label] = ret

    joined = pd.concat(rows.values(), axis=1, join="outer")
    joined.columns = list(rows.keys())
    return (joined["ustbond"] - joined["bund"]).rename("rate_support_score")


def classify_rates_ampel(
    rate_support_score: pd.Series, direction: pd.Series, z_window: int = 60, z_threshold: float = 0.5
) -> pd.Series:
    """grün (score supports the day's break direction, |z|>=threshold),
    rot (score opposes it, |z|>=threshold), gelb (everything else -
    including days with too little rolling history for a z-score yet).
    z-score is computed against a trailing window of PRIOR days' scores
    only (shift(1) before rolling) - no lookahead, and no fixed "typical
    daily move" assumed since bond-CFD volatility regimes drift over a
    multi-year backtest."""
    prior = rate_support_score.shift(1)
    rolling_std = prior.rolling(z_window, min_periods=z_window // 2).std()
    z = rate_support_score / rolling_std

    aligned = pd.Series(index=rate_support_score.index, dtype=object)
    z_al, dir_al = z.align(direction, join="left")
    sign_matches = np.sign(z_al) == dir_al
    confirmed = sign_matches & (z_al.abs() >= z_threshold)
    contradicted = (~sign_matches) & (z_al.abs() >= z_threshold) & dir_al.notna() & (dir_al != 0)

    out = pd.Series("gelb", index=rate_support_score.index)
    out[confirmed.fillna(False)] = "grün"
    out[contradicted.fillna(False)] = "rot"
    out[z_al.isna()] = "gelb"
    return out
