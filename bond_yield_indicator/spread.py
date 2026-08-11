"""Layer 1 (spread-core): the continuous, non-event-window version of the
paper's baseline spillover regression (Yildirim SSRN 6353258, Section 4,
eq. `Δ10yr_home = β0 + β1·Δ10yr_US`). Instead of estimating β1 only inside
FOMC windows on the full sample, this computes a daily yield-change spread
and z-scores it on a rolling window, so it can be read every trading day.

Resolution caveat (see fred.py docstring and the project note): the 6 non-US
countries are monthly FRED series. Forward-filling a monthly print onto a
daily grid means the "daily change" is zero on every day except the one
where a new monthly print rolls in - the spread signal for those 6
countries is therefore a step function, not a genuinely continuous daily
series like the paper's own data. This is disclosed, not hidden: `resolution`
on the output tells the caller which regime a country is in.

Publication-lag handling: OECD monthly series are dated to the FIRST of the
reference month (e.g. a value dated 2026-06-01 represents June's average)
but are not actually published/known that early - FRED itself typically
carries a 1-2 month lag for these mirrors. `publication_lag_days` shifts the
foreign series forward before the forward-fill to avoid the backtest seeing
a print before it was realistically knowable. The default (45 days) is a
disclosed, configurable assumption, not a verified per-country release
calendar - tightening it per country is future work if this becomes more
than a V1."""

import numpy as np
import pandas as pd

from bond_yield_indicator.fred import COUNTRIES, FREQUENCY, fetch_yield


def _daily_grid(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="D")


def aligned_yields(country: str, start: str, end: str, publication_lag_days: int = 45) -> pd.DataFrame:
    """US (daily) and `country` (possibly monthly, forward-filled with a
    publication lag) 10y yields on a common daily grid."""
    grid = _daily_grid(start, end)

    us = fetch_yield("US").reindex(grid).ffill()
    us.name = "us_yield"

    fx = fetch_yield(country)
    if FREQUENCY[country] == "monthly":
        fx = fx.copy()
        fx.index = fx.index + pd.Timedelta(days=publication_lag_days)
    fx = fx.reindex(fx.index.union(grid)).ffill().reindex(grid)
    fx.name = "foreign_yield"

    out = pd.concat([us, fx], axis=1)
    out.index.name = "date"
    return out


def yield_change_spread(country: str, start: str, end: str, publication_lag_days: int = 45) -> pd.DataFrame:
    """Δ10yr_US - Δ10yr_country per day (the sign convention in the project
    note's Layer 1: positive = US yields rising relative to `country`)."""
    y = aligned_yields(country, start, end, publication_lag_days)
    y["us_chg"] = y["us_yield"].diff()
    y["foreign_chg"] = y["foreign_yield"].diff()
    y["spread_chg"] = y["us_chg"] - y["foreign_chg"]
    y["resolution"] = FREQUENCY[country]
    return y


def zscore_spread(country: str, start: str, end: str, window: int = 60,
                   publication_lag_days: int = 45) -> pd.Series:
    """Rolling z-score of spread_chg - the stetig (continuous) analogue of
    the paper's within-FOMC-window standardized beta, computed every day
    instead of only inside event windows."""
    df = yield_change_spread(country, start, end, publication_lag_days)
    roll_mean = df["spread_chg"].rolling(window, min_periods=window // 2).mean()
    roll_std = df["spread_chg"].rolling(window, min_periods=window // 2).std()
    z = (df["spread_chg"] - roll_mean) / roll_std.replace(0, np.nan)
    return z.rename("z_spread")
