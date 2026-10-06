"""Unit-Tests fuer ny_open_orb.entries_nth (synthetische M1-Tage, Range 98-100)."""
import pandas as pd
import pytest

from ny_open_orb.entries_nth import find_entries_nth

HI, LO = 100.0, 98.0


def _day(path, date="2026-01-05"):
    """path: Liste (high, low, close) je M1-Bar ab 09:45 NY."""
    tz = "America/New_York"
    idx = pd.date_range(f"{date} 09:45", periods=len(path), freq="1min", tz=tz)
    df = pd.DataFrame(path, columns=["high", "low", "close"], index=idx)
    df["open"] = df["close"]
    df["orb_high"], df["orb_low"], df["orb_width"], df["atr"] = HI, LO, HI - LO, 1.0
    df["range_end"] = pd.Timestamp(f"{date} 09:45", tz=tz)
    df["session_close"] = pd.Timestamp(f"{date} 16:00", tz=tz)
    df["session"] = pd.Timestamp(date)
    return df


INSIDE = (99.5, 98.5, 99.0)
UP = (100.5, 99.5, 100.2)        # bricht oben, schliesst draussen
DOWN = (98.5, 97.5, 97.8)        # bricht unten, schliesst draussen
BOTH = (100.5, 97.5, 99.0)
ALL = {pd.Timestamp("2026-01-05"): [1, -1]}
LONG = {pd.Timestamp("2026-01-05"): [1]}


def _one(df, allowed, mode, **kw):
    e = find_entries_nth(df, allowed, mode, **kw)
    return None if e.empty else (e.entry_time.iloc[0].strftime("%H:%M"), int(e.direction.iloc[0]), e.entry_price.iloc[0])


def test_first_takes_first_break():
    df = _day([INSIDE, UP, INSIDE, DOWN])
    assert _one(df, ALL, "first") == ("09:46", 1, HI)


def test_first_ignores_disallowed_side_and_skips_double_bar():
    df = _day([INSIDE, DOWN, BOTH, INSIDE, UP])
    assert _one(df, LONG, "first") == ("09:47", 1, HI)   # nur long erlaubt: Doppel-Bar zaehlt als Long-Touch
    assert _one(df, ALL, "first") == ("09:46", -1, LO)


def test_nth_same_needs_return_into_range():
    df = _day([UP, UP, INSIDE, UP, INSIDE, UP])
    assert _one(df, ALL, "nth_same", n=2) == ("09:48", 1, HI)   # 2. Bruch erst nach Rueckkehr
    assert _one(df, ALL, "nth_same", n=3) == ("09:50", 1, HI)
    assert _one(_day([UP, UP, UP]), ALL, "nth_same", n=2) is None


def test_after_fail_requires_failed_opposite_side():
    df = _day([DOWN, INSIDE, UP])
    assert _one(df, ALL, "after_fail") == ("09:47", 1, HI)
    assert _one(_day([INSIDE, UP]), ALL, "after_fail") is None
    assert _one(_day([DOWN, UP]), ALL, "after_fail") is None   # keine Rueckkehr per Schluss


def test_fade_trades_against_first_break():
    assert _one(_day([INSIDE, UP]), ALL, "fade") == ("09:46", -1, HI)
    assert _one(_day([DOWN]), ALL, "fade") == ("09:45", 1, LO)
    assert _one(_day([INSIDE, UP]), LONG, "fade") is None


def test_retest_fills_on_return_to_level_and_cancels_on_opposite():
    df = _day([UP, (101.0, 100.4, 100.8), (100.6, 99.9, 100.3)])
    assert _one(df, ALL, "retest") == ("09:47", 1, HI)
    assert _one(_day([UP, (100.5, 97.5, 98.0)]), ALL, "retest") is None


def test_cutoff_blocks_late_entries():
    df = _day([INSIDE] * 30 + [UP])     # Bruch um 10:15
    assert _one(df, ALL, "first", cutoff="10:00") is None
    assert _one(df, ALL, "first", cutoff="11:00") == ("10:15", 1, HI)


def test_double_bar_skips_day_for_non_first_modes():
    assert _one(_day([BOTH, UP]), ALL, "fade") is None


def test_unknown_mode():
    with pytest.raises(ValueError):
        find_entries_nth(_day([INSIDE]), ALL, "zweiter")
