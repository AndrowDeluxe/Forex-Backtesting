"""Layer 2 (event-timing / sensitivity weight): the continuous analogue of
the paper's Table 1 standardized beta (Yildirim SSRN 6353258, Section 4),
computed on a trailing rolling window instead of the full sample, so it can
be used as a live sensitivity weight rather than a one-off historical
statistic.

Two estimators, dispatched automatically on fred.FREQUENCY[country]:

`rolling_beta_daily` - the paper-faithful version: OLS of Δforeign_yield on
    Δus_yield, restricted to days inside the 3-day FOMC event window,
    trailing `window_days` calendar days. Only meaningful for a daily-
    resolution country.

`rolling_beta_monthly` - for the 6 FRED-monthly countries in this project's
    current V1: restricting to FOMC-window DAYS would regress almost
    entirely on foreign_chg==0 observations, since a monthly print rolling
    in essentially never coincides with the ~3 FOMC-window days per meeting
    - the beta would silently collapse to ~0 and look like "no spillover"
    when it is really just a resolution artefact. Documented here rather
    than hidden: this estimator instead aggregates to the country's own
    print-to-print intervals (Δforeign_print vs. ΔUS over the same
    interval), trailing `window_prints` monthly observations. This is the
    correct estimator AT THE RESOLUTION THE DATA ACTUALLY SUPPORTS - not a
    fix for the resolution problem, just an honest fit to it. Swapping a
    country to a daily source later (see fred.py) is what makes
    rolling_beta_daily apply to it; no other code changes."""

import numpy as np
import pandas as pd

from bond_yield_indicator.calendar import BANK_BY_COUNTRY, event_window_dummy
from bond_yield_indicator.fred import FREQUENCY, fetch_yield
from bond_yield_indicator.spread import aligned_yields


def _ols_beta(x: pd.Series, y: pd.Series) -> float:
    """Simple OLS slope of y on x (no intercept needed, we only want beta1);
    returns NaN if too few points or x has no variance."""
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]
    if len(x) < 5 or x.std() == 0:
        return np.nan
    x_c = x - x.mean()
    y_c = y - y.mean()
    denom = (x_c ** 2).sum()
    return float((x_c * y_c).sum() / denom) if denom > 0 else np.nan


def rolling_beta_daily(country: str, start: str, end: str, window_days: int = 730,
                        event_window_days: int = 1, step_days: int = 5) -> pd.Series:
    y = aligned_yields(country, start, end)
    y["us_chg"] = y["us_yield"].diff()
    y["foreign_chg"] = y["foreign_yield"].diff()

    bank = BANK_BY_COUNTRY[country]
    is_event = event_window_dummy(bank, y.index, window_days=event_window_days).astype(bool)

    out = pd.Series(np.nan, index=y.index, name="beta_rolling")
    idx_positions = range(0, len(y.index), step_days)
    for pos in idx_positions:
        t = y.index[pos]
        window_start = t - pd.Timedelta(days=window_days)
        mask = (y.index > window_start) & (y.index <= t) & is_event
        out.loc[t] = _ols_beta(y.loc[mask, "us_chg"], y.loc[mask, "foreign_chg"])
    return out.ffill()


def rolling_beta_monthly(country: str, start: str, end: str, window_prints: int = 24) -> pd.Series:
    us = fetch_yield("US")
    fx = fetch_yield(country)
    fx = fx[(fx.index >= pd.Timestamp(start) - pd.Timedelta(days=400)) & (fx.index <= pd.Timestamp(end))]

    us_at_print = us.reindex(us.index.union(fx.index)).ffill().reindex(fx.index)
    prints = pd.DataFrame({"foreign": fx, "us": us_at_print}).dropna()
    prints["foreign_chg"] = prints["foreign"].diff()
    prints["us_chg"] = prints["us"].diff()
    prints = prints.dropna()

    betas = pd.Series(index=prints.index, dtype=float, name="beta_rolling")
    for i in range(len(prints)):
        lo = max(0, i - window_prints + 1)
        window = prints.iloc[lo:i + 1]
        betas.iloc[i] = _ols_beta(window["us_chg"], window["foreign_chg"])

    grid = pd.date_range(start, end, freq="D")
    return betas.reindex(betas.index.union(grid)).ffill().reindex(grid).rename("beta_rolling")


def rolling_beta(country: str, start: str, end: str, **kwargs) -> pd.Series:
    if FREQUENCY[country] == "daily":
        return rolling_beta_daily(country, start, end, **kwargs)
    return rolling_beta_monthly(country, start, end, **kwargs)
