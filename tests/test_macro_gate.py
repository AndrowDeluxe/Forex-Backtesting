"""CTNL-Makro-Sperre (gold_smc_htf_ltf/macro_gate.py): Richtung, Vortageswert, Fail-safe, getrackte Zeilen."""
import pandas as pd
import pytest

from gold_smc_htf_ltf import macro_gate as mg


@pytest.fixture
def fake(monkeypatch):
    s = pd.Series([80.0, 20.0, 50.0], index=pd.to_datetime(["2026-11-02", "2026-11-03", "2026-11-04"]))
    monkeypatch.setattr(mg, "_series", lambda: s)
    return s


def test_direction_rules(fake):
    assert mg.decide(-1, "2026-11-03 10:00")[0] is False   # Vortag 80 -> kein Short
    assert mg.decide(1, "2026-11-03 10:00")[0] is True
    assert mg.decide(1, "2026-11-04 10:00")[0] is False    # Vortag 20 -> kein Long
    assert mg.decide(-1, "2026-11-04 10:00")[0] is True
    assert mg.decide(1, "2026-11-05 10:00")[0] is True     # 50 neutral


def test_tz_aware_entry_uses_utc_day(fake):
    # 2026-11-04 00:30 UTC = 2026-11-03 19:30 New York -> Entry-Tag ist der 04. (UTC), Vortag 20
    t = pd.Timestamp("2026-11-03 19:30", tz="America/New_York")
    assert mg.decide(1, t)[0] is False


def test_stale_or_missing_passes(fake, monkeypatch):
    ok, grund = mg.decide(1, "2026-11-20 10:00")          # Wert 16 Tage alt
    assert ok and "veraltet" in grund
    monkeypatch.setattr(mg, "_series", lambda: (_ for _ in ()).throw(FileNotFoundError()))
    assert mg.decide(1, "2026-11-05")[0] is True


def test_filter_keeps_tracked_rows(fake):
    t = pd.DataFrame({"entry_time": pd.to_datetime(["2026-11-04 10:00", "2026-11-04 11:00", "2026-11-04 12:00"]),
                      "direction": [1, 1, -1]})
    out, hinweis = mg.filter_trades(t, lambda r: r["entry_time"].hour == 10)
    assert list(out["entry_time"].dt.hour) == [10, 12]     # 10 getrackt, 11 Long gesperrt, 12 Short ok
    assert "1 gegen MACRO gesperrt" in hinweis
