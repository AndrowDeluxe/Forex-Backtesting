"""Ereignisstudie CPI/NFP: Markierungen ohne Vorgriff (26.11.2026)."""

import numpy as np
import pandas as pd

from scripts.research_ereignisstudie_cpi_nfp import flag_trades, price_change, weak_at


def test_flag_trades_windows():
    ev = pd.DatetimeIndex(["2024-01-05 13:30"])
    tr = pd.DataFrame({
        "entry_time": pd.to_datetime(["2024-01-04 10:00", "2024-01-05 09:00", "2024-01-05 14:00", "2024-01-08 10:00"]),
        "exit_time": pd.to_datetime(["2024-01-06 10:00", "2024-01-05 12:00", "2024-01-05 16:00", "2024-01-09 10:00"]),
        "r": [1.0, 1.0, 1.0, 1.0], "leg": "x"})
    f = flag_trades(tr, ev)
    assert f["offen_ueber_termin"].tolist() == [True, False, False, False]
    assert f["einstieg_termintag_vorher"].tolist() == [False, True, False, False]
    assert f["einstieg_termintag_nachher"].tolist() == [False, False, True, False]


def test_weak_at_uses_only_earlier_releases():
    g = pd.DataFrame({"time": pd.to_datetime(["2024-01-02", "2024-02-01"], utc=True), "currency": "EUR",
                      "art": "pmi", "v": [52.0, 45.0]})
    assert weak_at(g, "EUR", pd.Timestamp("2024-01-15", tz="UTC")) is False  # PMI 45 erst spaeter bekannt
    assert weak_at(g, "EUR", pd.Timestamp("2024-02-02", tz="UTC")) is True
    assert weak_at(g, "USD", pd.Timestamp("2024-02-02", tz="UTC")) is None


def test_price_change_excludes_release_bar_on_h1():
    idx = pd.date_range("2024-01-05 12:00", periods=4, freq="h", tz="UTC")
    bars = pd.DataFrame({"Open": [1.0, 1.1, 1.2, 1.3], "Close": [1.1, 1.2, 1.3, 1.4]}, index=idx)
    # Termin 13:30 liegt in der 13:00-Kerze -> Vorher = deren Open (1.1), nachher = Schluss der 14:00-Kerze (1.3)
    assert np.isclose(price_change(bars, pd.Timestamp("2024-01-05 13:30", tz="UTC")), np.log(1.3 / 1.1))
