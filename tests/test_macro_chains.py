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


def test_ki_ketten_15_11():
    """Danske-KI-Ketten (15.11.): KOSPI treibt risiko_an_ki, HYG/IEF ersetzt FRED-HY."""
    m = {"kospi_20d": 7.0, "vix_20d": -2.0, "hyg_ief_20d": -3.0, "vix": 15.0,
         "korea_exporte_yoy_3m": 8.0, "china_importpreise_yoy": 3.2, "china_importpreise_yoy_3m": 2.0,
         "us_2y_20d_bp": 15.0, "kupfer_20d": 6.0}
    out = _by_id(chains.evaluate(m, None))
    for cid in ["risiko_an_ki", "ki_schulden_hy", "ki_chips_korea", "china_preise_inflation", "kupfer_aud_ki"]:
        assert out[cid]["status"] == "aktiv", cid
    m["hyg_ief_20d"] = 0.5
    assert _by_id(chains.evaluate(m, None))["ki_schulden_hy"]["status"] == "gestoppt"


def test_yoy_monthly_ignores_daily_gaps():
    idx = pd.date_range("2025-01-01", periods=15, freq="MS")
    s = pd.Series(range(100, 115), index=idx, dtype=float).reindex(pd.date_range("2025-01-01", "2026-03-01"))
    yoy = chains._yoy_monthly(s)
    assert len(yoy) == 3 and abs(yoy.iloc[0] - 12.0) < 1e-9


def test_umgekehrt_dreht_wirkung_und_geht_ins_ledger():
    """24.11.: Brent −13 %, 2J −24 bp -> Oel-Fed-Gold-Kette laeuft rueckwaerts (Gold-Rueckenwind)."""
    m = {"brent_20d": -13.0, "fed_kanal": True, "us_2y_20d_bp": -24.0}
    c = _by_id(chains.evaluate(m, None))["oel_fed_gold"]
    assert c["status"] == "umgekehrt" and c["ledger_assets"]["gold"] == +1
    rec = [r for r in ledger.records({"stand": "2026-11-24", "ketten": [c]}) if r["art"] == "kette"]
    gold = [r for r in rec if r["objekt"] == "oel_fed_gold:gold"][0]
    assert gold["richtung"] == +1 and gold["begruendung"].startswith("umgekehrt")
    m["us_2y_20d_bp"] = 0.0  # Brent faellt, aber kein Zins-Durchgriff -> nur gestoppt
    assert _by_id(chains.evaluate(m, None))["oel_fed_gold"]["status"] == "gestoppt"


def test_education_ketten_24_11():
    m = {"net_liq_13w": 200.0, "real_10y": 1.8, "real_10y_20d_bp": 25.0, "us_2y_20d_bp": -15.0,
         "us_kurve_20d_bp": 8.0, "usdjpy_20d": 3.0, "spx_20d": 4.0, "ust_jgb_20d_bp": 20.0,
         "erstantraege_vs_tief_pct": 20.0, "sahm": 0.35, "usd_ueberraschung": 3.0, "gdpnow": 2.0}
    out = _by_id(chains.evaluate(m, None))
    for cid in ["liquiditaet_risiko", "realzins_risiko", "kurve_dollar", "carry_risiko", "ust_jgb_usdjpy",
                "arbeitsmarkt_abschwung", "daten_ueberraschung_usd"]:
        assert out[cid]["status"] == "aktiv", cid
    m.update(net_liq_13w=-200.0, usdjpy_20d=-3.0, spx_20d=-4.0)
    out = _by_id(chains.evaluate(m, None))
    assert out["liquiditaet_risiko"]["status"] == "umgekehrt"
    assert out["liquiditaet_risiko"]["ledger_assets"] == {"spx": -1, "ndx": -1, "gold": -1}
    assert out["carry_risiko"]["status"] == "umgekehrt"


def test_measures_from_desk_blocks():
    sheet = {"desk": {"liquiditaet": {"chg_13w_mrd": 32.7, "sofr_iorb_bp": 2.0},
                      "zinsvol": {"move": 98.9},
                      "wachstum": {"gdpnow": 3.2, "sahm": 0.0, "erstantraege_4w_tsd": 198.0,
                                   "erstantraege_52w_tief_tsd": 180.0}},
             "scorecard": {"waehrungen": {"USD": {"ueberr_60t": 9.0}}}}
    m = chains.measures(pd.DataFrame(), pd.DataFrame(), sheet)
    assert m["net_liq_13w"] == 32.7 and m["move"] == 98.9 and m["usd_ueberraschung"] == 9.0
    assert abs(m["erstantraege_vs_tief_pct"] - 10.0) < 1e-9
