"""Stage 1 - pure range mechanics, no entries/exits yet (Phase 1-3 of the
repo's 8-phase checklist, folded into one script since this is the user's
own idea, not a paper to screen). Before building any of the four entry
types, sanity-check: how often does the NY-open opening range (first M15
bar after 09:30 America/New_York) get broken at all, in which direction,
and how often is it merely "tested" (wicked but never closed through) - the
precondition `fractal_reversal` in ny_open_orb/engine.py relies on. Also
checks the two range_bars variants (1 M15 bar = 15 min vs. 2 = 30 min) and
prints a per-year breakdown, since a range mechanic that looks fine pooled
but is dominated by one or two years would be a red flag before any entry
logic gets built on top of it.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.range import attach_orb_levels, compute_session_range

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"


def session_outcomes(m5: pd.DataFrame, session_range: pd.DataFrame) -> pd.DataFrame:
    """One row per session: whether it ever closed beyond orb_high/orb_low
    (confirmed break) and, if not, whether it ever wicked beyond either
    (tested-only) - the exact precondition fractal_reversal checks bar by
    bar in engine.py, computed here directly from the whole day for a
    cross-check."""
    attached = attach_orb_levels(m5, session_range)
    tradeable = attached[attached.index >= attached["range_end"]]
    tradeable = tradeable[tradeable.index < tradeable["session_close"]]
    tradeable = tradeable.dropna(subset=["orb_high"])

    rows = []
    for session, day in tradeable.groupby("session"):
        orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
        broke_up = (day["close"] > orb_high).any()
        broke_down = (day["close"] < orb_low).any()
        wicked_up = (day["high"] >= orb_high).any()
        wicked_down = (day["low"] <= orb_low).any()
        if broke_up and broke_down:
            outcome = "broke_both"
        elif broke_up:
            outcome = "broke_up"
        elif broke_down:
            outcome = "broke_down"
        elif wicked_up or wicked_down:
            outcome = "tested_only"
        else:
            outcome = "stayed_inside"
        rows.append({"session": session, "outcome": outcome, "orb_width": day["orb_width"].iloc[0]})
    return pd.DataFrame(rows).set_index("session")


def run(range_bars: int):
    print(f"\n{'=' * 30} range_bars={range_bars} ({15 * range_bars} min range) {'=' * 30}")
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    session_range = compute_session_range(m15, range_bars=range_bars)
    outcomes = session_outcomes(m5, session_range)

    print(f"\nTotal sessions with a formed range: {len(outcomes)}")
    print("\nOutcome distribution (pooled, all years):")
    print(outcomes["outcome"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

    print("\nMedian orb_width (points) by year:")
    outcomes["year"] = outcomes.index.year
    print(outcomes.groupby("year")["orb_width"].median().round(2))

    print("\nOutcome distribution by year (%):")
    by_year = pd.crosstab(outcomes["year"], outcomes["outcome"], normalize="index").mul(100).round(1)
    print(by_year)


def main():
    for range_bars in (1, 2):
        run(range_bars)


if __name__ == "__main__":
    main()
