import json
import sys

import pandas as pd

from asian_range_breakout import pending as P

FILTERS = {"day": "2026-11-03", "gold_close_prior": 4000.0, "gold_sma_prior": 4100.0, "silver_chg": -1.2,
           "friction_prior": 0.010, "friction_thr": 0.018, "friction_date": "2026-11-02"}


def _setup(status="setup", adx=22.0):
    return {"day": "2026-11-03", "status": status, "adx": adx, "detail": "x"}


def test_journal_only_in_bridge_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "Repo" / "run_once.py")])
    assert P.journal_path() is None
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "EK-Portfolio-Bridge" / "run_once.py")])
    assert P.journal_path() == tmp_path / "EK-Portfolio-Bridge" / "logs" / P.JOURNAL_NAME


def test_journal_writes_once_per_decision(tmp_path):
    path = tmp_path / "logs" / P.JOURNAL_NAME
    P._journal(_setup(status="range_not_ready"), FILTERS, path)
    assert not path.exists()
    P._journal(_setup(), FILTERS, path)
    P._journal(_setup(), FILTERS, path)          # gleicher Stand -> keine zweite Zeile
    P._journal(_setup(status="breakout_passed"), FILTERS, path)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert [r["status"] for r in rows] == ["setup", "breakout_passed"]
    assert rows[0]["filter_direction"] == -1 and rows[0]["friction_date"] == "2026-11-02"
    j = P.read_journal(path)
    assert j == {"2026-11-03": {"filter_direction": -1, "adx": 22.0}}


def test_journal_error_never_raises(tmp_path, capsys):
    blocker = tmp_path / "logs"
    blocker.write_text("kein Ordner")             # mkdir scheitert
    P._journal(_setup(), FILTERS, blocker / P.JOURNAL_NAME)
    assert "nicht geschrieben" in capsys.readouterr().out


def _trades(rows):
    return pd.DataFrame({"entry_time": pd.to_datetime([r[0] for r in rows]).tz_localize(P.NY),
                         "direction": [r[1] for r in rows], "delay_bars": [0] * len(rows)})


def test_apply_journal_follows_bot_and_reports_drift(monkeypatch):
    import asian_range_breakout.filters as F
    monkeypatch.setattr(F, "apply_entry_delay_filter", lambda t, max_delay_bars: t)
    raw = _trades([("2026-11-03 01:30", "short"), ("2026-11-04 01:30", "long"), ("2026-10-01 01:30", "long")])
    filtered = raw.iloc[[1, 2]]                   # Nachrechnung: 03.11. gefiltert
    journal = {"2026-11-03": {"filter_direction": -1, "adx": 20.0},
               "2026-11-04": {"filter_direction": None, "adx": 20.0}}
    out, drift = P._apply_journal(raw, filtered, journal)
    days = list(P._trade_day(out))
    assert days == ["2026-10-01", "2026-11-03"]   # 01.10. ohne Protokoll -> Filterkette
    assert drift == ["2026-11-03", "2026-11-04"]
