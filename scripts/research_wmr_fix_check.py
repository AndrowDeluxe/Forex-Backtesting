"""Sanity check for Evans (2017) "Forex Trading and the WMR Fix" -- see
app_pages/fx_papers_202608.py Tab 4. NOT a new trading strategy: a pure
correlation statistic testing whether Evans' negative pre/post-4pm-Fix
serial correlation (found on 2004-2013 data, attributed to dealer collusion
closed by the 2015 fixing-window reform) still holds on this repo's own
data when split before vs. after the reform.

Reuses the exact same M5 Dukascopy cache as
scripts/research_intraday_momentum.py (`intraday_momentum/data.py`) -- run
that script first, or this one will trigger the same (slow) fetch itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from intraday_momentum.data import PAIRS, load_all_pairs_m5
from intraday_momentum.wmr_fix import compute_pre_post_fix_changes, correlation_report

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2012-01-01", "2026-08-01"
HORIZONS = [30, 15, 5]  # minutes each side of 16:00 London; 5 min = M5's resolution floor


def main():
    print(f"Loading M5 Dukascopy history for {PAIRS} ({START} .. {END}), reusing intraday_momentum's cache...")
    data = load_all_pairs_m5(START, END)

    rows = []
    for pair in PAIRS:
        for horizon in HORIZONS:
            fix_changes = compute_pre_post_fix_changes(data[pair], horizon_minutes=horizon)
            report = correlation_report(fix_changes)
            for split_name, stats in report.items():
                rows.append({"pair": pair, "horizon_min": horizon, "split": split_name, **stats})
        print(f"  {pair} done")

    results = pd.DataFrame(rows).set_index(["pair", "horizon_min", "split"])
    print("\n=== Pre/Post-Fix serial correlation, pre- vs. post-2015-reform, EOM vs. intra-month ===")
    print(results)

    print("\n=== Headline: pre- vs. post-reform correlation at 30-min horizon, all pairs ===")
    headline = results.xs(30, level="horizon_min").unstack("split")["corr"][
        ["pre_reform", "post_reform", "pre_reform_eom", "post_reform_eom"]
    ]
    print(headline)

    print(
        "\nInterpretation guide: Evans (2017) found consistently NEGATIVE correlation pre-2015 "
        "(strongest at month-end). If the collusion explanation is right, post-reform correlation "
        "should be weaker/closer to zero than pre-reform, on the same pair/horizon."
    )
    return results


if __name__ == "__main__":
    main()
