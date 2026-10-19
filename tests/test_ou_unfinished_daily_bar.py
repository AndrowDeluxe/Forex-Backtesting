import pandas as pd

from challenge_portfolio.paper_bot import _drop_unfinished_daily_bar


def _panel(tz=None):
    idx = pd.date_range("2026-10-13", "2026-10-16", freq="D", tz=tz)  # Di-Fr
    return pd.DataFrame({"EOG": [1.0, 2.0, 3.0, 4.0]}, index=idx)


def _last_date(df):
    return pd.DatetimeIndex(df.index).date[-1].isoformat()


def test_during_session_drops_todays_bar():
    # Fr 16.10. 15:13 UTC = 11:13 New York: die 16.10.-Kerze ist noch vorlaeufig.
    out = _drop_unfinished_daily_bar(_panel(), pd.Timestamp("2026-10-16 15:13"))
    assert _last_date(out) == "2026-10-15"


def test_after_close_still_drops_todays_bar():
    # 21:30 UTC = 17:30 New York: Eingestiegen wird ohnehin erst zur naechsten Eroeffnung.
    out = _drop_unfinished_daily_bar(_panel(), pd.Timestamp("2026-10-16 21:30"))
    assert _last_date(out) == "2026-10-15"


def test_utc_midnight_uses_new_york_date():
    # Sa 17.10. 02:00 UTC ist in New York noch Fr 16.10. 22:00.
    out = _drop_unfinished_daily_bar(_panel(), pd.Timestamp("2026-10-17 02:00"))
    assert _last_date(out) == "2026-10-15"


def test_next_day_keeps_yesterdays_bar():
    # Mo 19.10. 14:00 UTC = 10:00 New York: die Freitagskerze ist fertig und bleibt.
    out = _drop_unfinished_daily_bar(_panel(), pd.Timestamp("2026-10-19 14:00"))
    assert _last_date(out) == "2026-10-16"
    assert len(out) == 4


def test_tz_aware_index_and_end():
    out = _drop_unfinished_daily_bar(_panel(tz="America/New_York"),
                                     pd.Timestamp("2026-10-16 15:13", tz="UTC"))
    assert _last_date(out) == "2026-10-15"
