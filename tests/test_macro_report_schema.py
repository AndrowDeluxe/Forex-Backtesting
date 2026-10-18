"""Tests fuer fusion_lab/macro_reports (Schema + Backtest-Mechanik)."""

from types import SimpleNamespace

import pandas as pd
import pytest

from fusion_lab.macro_reports import backtest as bt
from fusion_lab.macro_reports.schema import Report, normalize_instrument


def test_normalize_instrument():
    assert normalize_instrument("EUR/USD") == "EURUSD"
    assert normalize_instrument("Gold") == "GOLD"
    assert normalize_instrument("US500") == "SP500"
    assert normalize_instrument("dxy") == "DXY"
    with pytest.raises(ValueError):
        normalize_instrument("FOO/BAR")


def test_levels_require_quote():
    base = {"msg_id": 1, "posted_utc": "2026-08-16T15:00:00+00:00", "generation": 3}
    ok = dict(instrument="GOLD", direction="long", role="main", status="aktiv", quote="q")
    Report.model_validate({**base, "ideas": [ok]})
    with pytest.raises(ValueError):
        Report.model_validate({**base, "ideas": [{**ok, "stop": 4300.0}]})
    with pytest.raises(ValueError):
        Report.model_validate({**base, "ideas": [{**ok, "activation_price": 1.0, "level_quote": "x"}]})


class FakePrices:
    """H1-Pfad + konstante ATR, damit die Mechanik ohne Dukascopy pruefbar ist."""

    def __init__(self, bars, atr=1.0):
        idx = pd.date_range("2026-08-17 00:00", periods=len(bars), freq="h", tz="UTC")
        self._h1 = pd.DataFrame(bars, columns=["Open", "High", "Low", "Close"], index=idx)
        self._atr = atr

    def h1(self, key):
        return self._h1

    def atr(self, key, before):
        return self._atr


def _idea(**kw):
    d = dict(instrument="EURUSD", direction="long", role="main", status="aktiv", confidence=None,
             msg_id=1, generation=3, posted=pd.Timestamp("2026-08-16 23:30", tz="UTC"),
             stop=None, targets=[], invalidation_price=None)
    d.update(kw)
    return SimpleNamespace(**d)


def test_entry_strictly_after_post_time():
    h1 = FakePrices([[100, 100, 100, 100]] * 3)._h1
    assert bt._first_bar_after(h1, pd.Timestamp("2026-08-17 00:00", tz="UTC")) == 1
    assert bt._first_bar_after(h1, pd.Timestamp("2026-08-16 23:30", tz="UTC")) == 0


def test_stop_wins_when_stop_and_target_in_same_bar():
    # Einstieg 100, ATR-Stop 98.5 (1,5 x 1), Ziel 2 R = 103; Bar 2 beruehrt beides
    px = FakePrices([[100, 100.5, 99.5, 100], [100, 104, 98, 101]])
    t = bt._level_trade("B", _idea(), px, 0, None)
    assert t.exit_reason == "stop" and t.r_gross == pytest.approx(-1.0)


def test_report_stop_and_nearest_target_used():
    px = FakePrices([[100, 100.2, 99.8, 100], [100, 101.2, 99.9, 101]])
    t = bt._level_trade("B", _idea(stop=99.0, targets=[103.0, 101.0]), px, 0, 99.0)
    assert t.exit_reason == "target" and t.exit == 101.0 and t.r_gross == pytest.approx(1.0)


def test_wrong_side_stop_falls_back_to_atr():
    px = FakePrices([[100, 100.1, 99.9, 100], [100, 101.6, 99.9, 101]])
    t = bt._level_trade("B", _idea(direction="short"), px, 0, 99.0)  # Stop unter Short-Einstieg = ungueltig
    assert t.risk == pytest.approx(1.5) and t.exit_reason == "stop" and t.exit == pytest.approx(101.5)


def test_limit_entry_fills_on_pullback_and_uses_fill_as_entry():
    # Erste Eröffnung 100, ATR 1 -> Long-Limit 99.5; Bar 2 fällt auf 99.4 (Füllung), Bar 3 erreicht 2R = 102.5
    px = FakePrices([[100, 100.2, 99.8, 100], [99.9, 100, 99.4, 99.6], [99.6, 102.6, 99.5, 102.4]])
    t = bt._limit_trade(_idea(), px)
    assert t.variant == "D" and t.entry == pytest.approx(99.5)
    assert t.exit_reason == "target" and t.r_gross == pytest.approx(2.0)


def test_limit_entry_without_pullback_gives_no_trade():
    px = FakePrices([[100, 100.5, 99.9, 100.4]] * 80)  # nie 0,5 ATR unter Eröffnung, 80 h > 3 Handelstage
    assert bt._limit_trade(_idea(), px) is None


def test_v2_selection_keeps_only_unconditional_non_hedge():
    d = pd.DataFrame([
        dict(msg_id=1, instrument="EURUSD", direction="long", status="aktiv", role="main", confidence=None, idea_no=0, generation=3, activation_price=None),
        dict(msg_id=1, instrument="GOLD", direction="long", status="aktiv", role="hedge", confidence=None, idea_no=1, generation=3, activation_price=None),
        dict(msg_id=1, instrument="USDJPY", direction="short", status="event", role="event", confidence=None, idea_no=2, generation=3, activation_price=None),
        dict(msg_id=1, instrument="AUDUSD", direction="long", status="watch", role="secondary", confidence=None, idea_no=3, generation=3, activation_price=None),
    ])
    assert list(bt.select_ideas("A1", d, "v2").instrument) == ["EURUSD"]
