"""Tests fuer fusion_lab/news_sources (ohne Netz, ohne Claude)."""

from __future__ import annotations

import pandas as pd
import pytest

from fusion_lab.news_sources import classify, collectors, ledger, report
from fusion_lab.news_sources import config as C


def _items():
    return [
        {"symbol": "NVDA", "gruppe": "news", "quelle": "Google News: Reuters", "titel": "Nvidia falls 14% on SEC probe",
         "zeit": "2026-11-20 18:00", "link": "https://x/1"},
        {"symbol": "NVDA", "gruppe": "social", "quelle": "StockTwits", "titel": "oversold, buying", "zeit": "2026-11-20 19:00",
         "link": "https://x/2"},
        {"symbol": "GBPUSD", "gruppe": "news", "quelle": "Google News: FXStreet", "titel": "GBP/USD holds 1.2923",
         "zeit": "2026-11-17 09:00", "link": "https://x/3"},
    ]


def test_pack_ids_are_per_symbol_and_group():
    pack, index = classify.build_pack(_items())
    assert [e["id"] for e in pack["NVDA"]["news"]] == ["NVDA-n-1"]
    assert pack["NVDA"]["social"][0]["id"] == "NVDA-s-1"
    assert index["GBPUSD-n-1"]["link"] == "https://x/3"


def test_validator_drops_invented_ids_groups_and_markets():
    pack, index = classify.build_pack(_items())
    raw = {"NVDA": {"news": {"stimmung": -2, "kernaussage": "Nvidia faellt um 14%.", "ids": ["NVDA-n-1", "NVDA-n-9"]},
                    "offiziell": {"stimmung": 1, "kernaussage": "x", "ids": ["NVDA-o-1"]},
                    "social": {"stimmung": 1, "kernaussage": "ueberverkauft", "ids": ["GBPUSD-n-1"]}},
           "AAPL": {"news": {"stimmung": 2, "kernaussage": "x", "ids": []}}}
    out, warn = classify.validate(raw, pack, index)
    assert out["NVDA"]["news"]["ids"] == ["NVDA-n-1"]          # erfundene ID entfernt
    assert out["NVDA"]["news"]["wert"] == -1.0
    assert "offiziell" not in out["NVDA"]                       # Gruppe ohne Eintraege
    assert "social" not in out["NVDA"]                          # nur fremde ID zitiert -> verworfen
    assert "AAPL" not in out                                    # Markt nicht im Paket
    assert len(warn) >= 4


def test_number_check_accepts_decimal_comma_and_dates_but_flags_invented():
    belegt = "GBP/USD holds 1.2923 2026-11-17 09:00"
    assert classify.unbelegte_zahlen("Pfund haelt 1,2923 seit 17.11.", belegt) == []
    assert classify.unbelegte_zahlen("Ziel 1,3500", belegt) == ["1,3500"]


def test_stimmung_is_clipped():
    pack, index = classify.build_pack(_items())
    out, _ = classify.validate({"NVDA": {"news": {"stimmung": 7, "kernaussage": "", "ids": ["NVDA-n-1"]}}}, pack, index)
    assert out["NVDA"]["news"]["stimmung"] == 2


def test_missing_keys_mean_not_configured(monkeypatch):
    monkeypatch.setattr(collectors, "secrets", lambda: {})
    assert collectors.finnhub_news(["AAPL"])["status"] == "nicht konfiguriert"
    assert collectors.reddit(["AAPL"])["status"] == "nicht konfiguriert"
    assert collectors.alphavantage(["AAPL"])["status"] == "nicht konfiguriert"


def test_daily_only_source_skipped_outside_daily_run(monkeypatch):
    for name in list(collectors.TEXT_SOURCES) + list(collectors.NUMBER_SOURCES):
        if name not in C.DAILY_ONLY:
            monkeypatch.setitem(collectors.TEXT_SOURCES if name in collectors.TEXT_SOURCES else collectors.NUMBER_SOURCES,
                                name, lambda s: {"status": "ok", "grund": "", "items": [], "werte": []})
    out = collectors.collect(["AAPL"], daily=False)
    assert out["alphavantage"]["status"] == "nur Tageslauf"


def test_broken_source_never_stops_the_run(monkeypatch):
    def boom(_s):
        raise RuntimeError("kaputt")
    monkeypatch.setitem(collectors.NUMBER_SOURCES, "krypto_fear_greed", boom)
    for name in collectors.TEXT_SOURCES:
        monkeypatch.setitem(collectors.TEXT_SOURCES, name, lambda s: {"status": "ok", "grund": "", "items": []})
    for name in ("cnn_fear_greed", "alphavantage"):
        monkeypatch.setitem(collectors.NUMBER_SOURCES, name, lambda s: {"status": "ok", "grund": "", "werte": []})
    out = collectors.collect(["BTC"], daily=True)
    assert out["krypto_fear_greed"]["status"] == "fehler"
    assert out["google_news"]["status"] == "ok"


def test_rss_parser_handles_bom():
    xml = "﻿<?xml version='1.0' encoding='utf-8'?><rss><channel><item><title>FOMC minutes</title>" \
          "<link>https://fed/1</link><pubDate>Wed, 18 Nov 2026 19:00:00 GMT</pubDate></item></channel></rss>"
    items = collectors._rss_items(xml.encode("utf-8"))
    assert items[0]["titel"] == "FOMC minutes" and items[0]["t"].year == 2026


def _snap(day="2026-11-20"):
    return {"datum": day, "zeit": f"{day}T22:30:00+01:00", "symbole": ["NVDA", "BTC"],
            "quellen": {"google_news": {"status": "ok", "grund": "", "eintraege": 3}},
            "items": [], "werte": [{"symbol": "BTC", "quelle": "krypto_fear_greed", "roh": 12, "wert": -0.76, "n": 1},
                                   {"symbol": "NVDA", "quelle": "stocktwits", "roh": "1/1", "wert": None, "n": 2}],
            "claude": {"status": "ok", "grund": "", "warnungen": [],
                       "ergebnis": {"NVDA": {"news": {"stimmung": -2, "wert": -1.0, "ids": ["a", "b"]}}}}}


def test_ledger_appends_once_per_day(tmp_path):
    led, runs = tmp_path / "w.csv", tmp_path / "l.csv"
    assert ledger.append(_snap(), led, runs) == 3
    assert ledger.append(_snap(), led, runs) == 0           # zweiter Lauf am selben Tag aendert nichts
    df = ledger.read(led)
    assert set(df["quelle"]) == {"krypto_fear_greed", "stocktwits", "claude_news"}
    assert df.loc[df["quelle"] == "stocktwits", "status"].iat[0] == "zu wenig Daten"
    assert len(pd.read_csv(runs)) == 4                       # 2 Laeufe x (1 Quelle + claude)


def test_forward_returns_start_after_record_day_no_lookahead():
    led = pd.DataFrame([{"datum": "2026-11-20", "symbol": "NVDA", "klasse": "aktien", "quelle": "claude_news",
                         "wert": -1.0, "status": "ok"}])
    idx = pd.to_datetime(["2026-11-19", "2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25"])
    prices = pd.DataFrame({"NVDA": [100, 50, 200, 180, 190]}, index=idx)   # 20.11. (Aufzeichnungstag) zaehlt nicht
    out = report.forward_returns(led, prices)
    assert out["ret_1"].iat[0] == pytest.approx(-10.0)        # 23.11. -> 24.11.
    assert out["ret_3"].isna().iat[0]                          # Horizont noch nicht erreicht


def test_evaluate_reports_edge_over_market_direction():
    rows = []
    for i in range(80):
        up = i % 2 == 0
        rows.append({"quelle": "q", "klasse": "aktien", "status": "ok", "wert": 1.0 if up else -1.0,
                     "ret_1": 1.0 if up else -1.0, "ret_3": None, "ret_5": None, "ret_10": None})
    ev = report.evaluate(pd.DataFrame(rows))
    r = ev[ev["horizont"] == 1].iloc[0]
    assert r["treffer"] == 1.0 and r["kontrolle"] == 0.5 and r["vorsprung"] == 0.5
    assert bool(r["aussagekraeftig"]) is True
