"""Central-bank meeting calendars and the 3-day event-window dummy from
Yildirim (SSRN 6353258), Section 5: D_FOMC_t = 1 on the day before, the day
of, and the day after a meeting. Same construction applies per-bank for the
6 foreign central banks.

Two static CSVs, both derived programmatically (not hand-typed) - see
bond_yield_indicator/_calendar_build/ for the derivation scripts:
    data_cache/bond_yield_indicator/cb_calendar_paper.csv
        ECB/BoE/BoJ/BoC/SNB/RBA meeting dates 1997-2024, parsed from the
        paper's own Appendix B tables 4-9 (row counts cross-checked against
        each table's declared N during parsing - 6 rows across ~1400 dates
        showed the table's own declared N one short of the actual date list;
        treated as a paper-side count typo, not a transcription error, since
        the mismatch always runs declared-N < parsed-count).
    data_cache/bond_yield_indicator/fomc_calendar.csv
        FOMC meeting/announcement dates 2016-2026 (the paper's own appendix
        does not list Fed dates), scraped from federalreserve.gov's
        historical-materials and current-calendar pages, announcement date =
        last day of each meeting. Materialized as a static file rather than
        scraped at runtime for backtest reproducibility.

Known gap: neither file extends past 2026. Extending is a matter of
appending rows to the CSVs (or writing a small updater against the same
federalreserve.gov / ECB / BoE / BoJ / BoC / SNB / RBA calendar pages), not a
code change here."""

from pathlib import Path

import pandas as pd

# Git-tracked (unlike data_cache/, which is gitignored): these two CSVs are
# hand-won reference data - paper-appendix tables and a one-off scrape - not
# disposable API cache, so they belong in the repo, not the cache bucket.
CACHE_DIR = Path(__file__).resolve().parent / "calendars"

BANKS = ["FOMC", "ECB", "BOE", "BOJ", "BOC", "SNB", "RBA"]

# country -> the bank whose meetings its 10y yield reacts to (per fred.py's
# COUNTRIES mapping; DE stands in for the Eurozone/ECB, as in the paper).
BANK_BY_COUNTRY = {"US": "FOMC", "DE": "ECB", "UK": "BOE", "JP": "BOJ",
                    "CA": "BOC", "CH": "SNB", "AU": "RBA"}


def _load_raw() -> pd.DataFrame:
    paper = pd.read_csv(CACHE_DIR / "cb_calendar_paper.csv", parse_dates=["date"])
    fomc = pd.read_csv(CACHE_DIR / "fomc_calendar.csv", parse_dates=["date"])
    return pd.concat([paper, fomc], ignore_index=True)


_RAW = None


def get_meetings(bank: str) -> pd.DatetimeIndex:
    """All known meeting/announcement dates for `bank` (one of BANKS)."""
    global _RAW
    if bank not in BANKS:
        raise ValueError(f"unknown bank {bank!r}, expected one of {BANKS}")
    if _RAW is None:
        _RAW = _load_raw()
    dates = _RAW.loc[_RAW["bank"] == bank, "date"]
    return pd.DatetimeIndex(sorted(dates.unique()))


def event_window_dummy(bank: str, date_index: pd.DatetimeIndex, window_days: int = 1) -> pd.Series:
    """D_bank_t: 1 for each date in `date_index` that falls within
    +/- window_days calendar days of a meeting date, else 0. window_days=1
    reproduces the paper's 3-day (day-before/of/after) window."""
    meetings = get_meetings(bank)
    dummy = pd.Series(0, index=date_index, dtype=int)
    if len(meetings) == 0:
        return dummy
    offsets = range(-window_days, window_days + 1)
    flagged = set()
    for m in meetings:
        for off in offsets:
            flagged.add(m + pd.Timedelta(days=off))
    dummy[:] = date_index.isin(flagged).astype(int)
    return dummy
