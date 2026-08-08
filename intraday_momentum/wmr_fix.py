"""WMR 4pm-Fix pre/post serial-correlation sanity check (Evans 2017 -- see
app_pages/fx_papers_202608.py Tab 4). NOT a new trading signal -- a
correlation statistic, reusing the same M5 Dukascopy data/cache as the
intraday-momentum research (`intraday_momentum/data.py`).

Evans (2017) finds significant NEGATIVE serial correlation between pre- and
post-4pm-London-Fix price changes on 2004-2013 data, and attributes it to
dealer collusion/front-running around the fix that the industry's 2015
reform (fixing window widened 1 -> 5 minutes) specifically targeted. This
module tests whether that negative correlation survives on this repo's own
data when split before vs. after the reform -- if the collusion story is
right, it should weaken or vanish post-reform.

Fix time: 16:00 London-local ("the London 4pm Fix"), located the same
DST-safe way as `signals.py`'s London-Open anchor (`tz_convert`). Minimum
resolvable horizon here is 5 minutes (M5 bars) -- Evans' most dramatic
figures use a 1-minute horizon, which M5 data cannot represent; this is a
real, disclosed resolution limit of this sanity check, not a design choice.
"""

import numpy as np
import pandas as pd

FIX_HOUR = 16

# The 5-minute methodology change was announced Oct. 2014; the widened
# fixing window itself went live in Feb. 2015 (Evans 2017, fn. 9; Chaboud
# et al. 2023, Sec. 6.2). Using the window-widening date as the cutoff.
REFORM_DATE = pd.Timestamp("2015-02-15")


def compute_pre_post_fix_changes(df: pd.DataFrame, horizon_minutes: int) -> pd.DataFrame:
    """One row per London-local calendar day with a resolvable fix window:
    date, pre_fix_return, post_fix_return (both log returns, `horizon_minutes`
    on each side of 16:00 London-local)."""
    df = df.sort_index().copy()
    london_local = df.index.tz_convert("Europe/London")
    df["_london_date"] = london_local.date
    df["_london_min"] = london_local.hour * 60 + london_local.minute

    fix_min = FIX_HOUR * 60
    pre_min = fix_min - horizon_minutes
    post_min = fix_min + horizon_minutes

    rows = []
    for london_date, day_df in df.groupby("_london_date"):
        pre_candidates = day_df.index[day_df["_london_min"] >= pre_min]
        fix_candidates = day_df.index[day_df["_london_min"] >= fix_min]
        post_candidates = day_df.index[day_df["_london_min"] >= post_min]
        if pre_candidates.empty or fix_candidates.empty or post_candidates.empty:
            continue
        pre_t, fix_t, post_t = pre_candidates[0], fix_candidates[0], post_candidates[0]
        if not (pre_t < fix_t < post_t):
            continue

        p_pre = float(day_df.loc[pre_t, "close"])
        p_fix = float(day_df.loc[fix_t, "close"])
        p_post = float(day_df.loc[post_t, "close"])
        if min(p_pre, p_fix, p_post) <= 0:
            continue

        rows.append(
            {
                "date": pd.Timestamp(london_date),
                "pre_fix_return": float(np.log(p_fix / p_pre)),
                "post_fix_return": float(np.log(p_post / p_fix)),
            }
        )
    return pd.DataFrame(rows)


def add_eom_flag(fix_changes: pd.DataFrame) -> pd.DataFrame:
    """Adds `is_eom`: True where `date` is the last (present) trading day of
    its calendar month -- Evans (2017)'s "last trading day of each month"."""
    out = fix_changes.copy()
    month_key = out["date"].dt.to_period("M")
    last_per_month = out.groupby(month_key)["date"].transform("max")
    out["is_eom"] = out["date"] == last_per_month
    return out


def correlation_report(fix_changes: pd.DataFrame) -> dict:
    """Pearson correlation(pre_fix_return, post_fix_return) + n, split by
    pre-/post-reform and by EOM/intra-month."""
    out = {}
    fc = add_eom_flag(fix_changes)
    splits = {
        "full_period": fc,
        "pre_reform": fc[fc["date"] < REFORM_DATE],
        "post_reform": fc[fc["date"] >= REFORM_DATE],
        "pre_reform_eom": fc[(fc["date"] < REFORM_DATE) & fc["is_eom"]],
        "pre_reform_intra": fc[(fc["date"] < REFORM_DATE) & ~fc["is_eom"]],
        "post_reform_eom": fc[(fc["date"] >= REFORM_DATE) & fc["is_eom"]],
        "post_reform_intra": fc[(fc["date"] >= REFORM_DATE) & ~fc["is_eom"]],
    }
    for name, subset in splits.items():
        if len(subset) < 10:
            out[name] = {"n": len(subset), "corr": np.nan}
            continue
        corr = float(subset["pre_fix_return"].corr(subset["post_fix_return"]))
        out[name] = {"n": len(subset), "corr": corr}
    return out
