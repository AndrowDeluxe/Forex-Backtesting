"""Makro-Agent v3 Phase 4: Wirkketten-Status und Ledger-Eintraege aktiver Ketten."""

import pandas as pd

from fusion_lab.macro_agent import chains, ledger


def _by_id(out):
    return {c["id"]: c for c in out}


def test_status_aktiv_anlaufend_gestoppt_ruhend():
    m = {"brent_20d": 8.0, "fed_kanal": True, "us_2y_20d_bp": 20.0, "us_2y_20d": None,
         "oat_bund_bp": 150.0, "oat_bund_20d_bp": 2.0, "vix": 15.0, "spx_5d": 0.0}
    out = _by_id(chains.evaluate(m, None))
    assert out["oel_fed_gold"]["status"] == "aktiv"
    assert out["defizit_oat"]["status"] == "anlaufend"
    assert out["risiko_aus_hafen"]["status"] == "gestoppt"  # VIX < 18
    m["brent_20d"] = -8.0
    assert _by_id(chains.evaluate(m, None))["oel_fed_gold"]["status"] == "gestoppt"


def test_missing_measure_never_activates():
    out = _by_id(chains.evaluate({}, None))
    assert all(c["status"] == "ruhend" for c in out.values())


def test_beleg_from_exposure():
    expo = {"us_2y": {"assets": {"Gold": {"status": "belegt", "heute": -1.2, "oos": -1.1},
                                 "USDJPY": {"status": "belegt", "heute": 0.4, "oos": 1.3},
                                 "EURUSD": {"status": "schwach", "heute": 0.1, "oos": -0.4}}}}
    c = _by_id(chains.evaluate({}, expo))["oel_fed_gold"]
    assert c["beleg"] == "teilweise" and len(c["beleg_details"]) == 3


def test_active_chain_goes_to_ledger():
    m = {"brent_20d": 8.0, "fed_kanal": True, "us_2y_20d_bp": 20.0}
    sheet = {"stand": "2026-11-12", "ketten": chains.evaluate(m, None)}
    rec = [r for r in ledger.records(sheet) if r["art"] == "kette"]
    objs = {r["objekt"]: (r["richtung"], r["messgroesse"]) for r in rec}
    assert objs["oel_fed_gold:gold"] == (-1, "gold") and all(r["horizont"] == 20 for r in rec)
