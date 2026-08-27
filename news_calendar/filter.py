"""Kombiniert fred_releases.py (US) + eurostat_calendar.py (EUR) zu einem
einzigen Datums-Set und einer Dummy-Funktion analog zu
bond_yield_indicator/calendar.py's event_window_dummy() -- 1 fuer jeden Tag,
der innerhalb +/- window_days eines US- oder EUR-High-Impact-Release liegt.

window_days=0 (Default) = "ganz simpler" Filter (nur der Release-Tag selbst),
wie vom User angefragt."""

import pandas as pd

from .eurostat_calendar import fetch_eur_release_dates_filtered
from .fred_releases import fetch_all_us_release_dates


def get_news_dates(start: str, end: str, force_refresh: bool = False) -> pd.DatetimeIndex:
    us = fetch_all_us_release_dates(start, end, force_refresh=force_refresh)
    eur = fetch_eur_release_dates_filtered()
    combined = pd.DatetimeIndex(sorted(set(us) | set(eur)))
    return combined[(combined >= pd.Timestamp(start)) & (combined <= pd.Timestamp(end))]


def news_day_dummy(date_index: pd.DatetimeIndex, start: str, end: str, window_days: int = 0) -> pd.Series:
    """1 fuer jedes Datum in `date_index`, das innerhalb +/- window_days eines
    US/EUR-News-Tages liegt, sonst 0. `date_index` kann jede Aufloesung haben
    (z.B. M5-Zeitstempel) -- der Vergleich laeuft ueber den normalisierten
    Kalendertag."""
    news_dates = get_news_dates(start, end)
    day_key = pd.DatetimeIndex(date_index).tz_localize(None).normalize() if date_index.tz else date_index.normalize()

    flagged: set[pd.Timestamp] = set()
    for d in news_dates:
        for off in range(-window_days, window_days + 1):
            flagged.add(d + pd.Timedelta(days=off))

    return pd.Series(day_key.isin(flagged), index=date_index)
