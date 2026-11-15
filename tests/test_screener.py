"""Tests fuer fusion_lab.screener (ohne Netz, ohne LLM)."""

import numpy as np
import pandas as pd
import pytest

from fusion_lab.screener import analyst, config as C, ledger, levels, scoring, universe


def _bars(closes, spread=1.0, start="2025-01-01"):
    c = np.asarray(closes, dtype=float)
    idx = pd.bdate_range(start, periods=len(c))
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) + spread, "Low": np.minimum(o, c) - spread,
                         "Close": c, "Volume": 1e6}, index=idx)


# ------------------------------------------------------------------ levels

def test_scenario_rules_hold():
    rng = np.random.default_rng(1)
    c = 100 + np.cumsum(rng.normal(0, 1.5, 400))
    sc = levels.scenarios(_bars(c))
    a, px = sc["atr"], sc["kurs"]
    if sc["A"]:
        A = sc["A"]
        assert C.A_MIN_ATR * a - 1e-6 <= px - A["zone_hi"] <= C.A_MAX_ATR * a + 0.01 * px
        assert A["stopp"] < A["zone_lo"] < A["einstieg"] < A["zone_hi"]
        assert A["rr"] >= C.MIN_RR
    if sc["B"]:
        B = sc["B"]
        assert B["trigger"] > px and B["stopp"] < B["trigger"] < B["ziel"] and B["rr"] >= C.MIN_RR - 1e-9
    for z in sc["zonen"]:
        assert z["hi"] - z["lo"] <= C.MAX_ZONE_ATR * a + C.MIN_ZONE_ATR * a + 1e-6


def test_clusters_do_not_chain():
    marks = [{"preis": 100 + 0.4 * k, "art": "x"} for k in range(30)]   # Kette im Abstand 0,4 ATR
    zones = levels.clusters(marks, a=1.0)
    assert len(zones) > 1
    assert all(z["hi"] - z["lo"] <= C.MAX_ZONE_ATR + 1e-9 for z in zones)


def test_scenario_prices_contains_levels():
    rng = np.random.default_rng(2)
    sc = levels.scenarios(_bars(100 + np.cumsum(rng.normal(0, 1, 300))))
    allowed = levels.scenario_prices(sc)
    for k in ("A", "B"):
        if sc[k]:
            assert sc[k]["stopp"] in allowed and sc[k]["ziel"] in allowed


# ------------------------------------------------------------------ scoring

def test_signal_thresholds():
    assert scoring.signal(65) == "KAUFEN" and scoring.signal(64.9) == "HALTEN"
    assert scoring.signal(35) == "VERKAUFEN" and scoring.signal(35.1) == "HALTEN"


def test_total_weights_sentiment():
    assert scoring.total(60, None) == 60
    assert scoring.total(60, 2) == pytest.approx(0.7 * 60 + 0.3 * 100)
    assert scoring.total(60, -2) == pytest.approx(0.7 * 60)


def test_stock_score_handles_missing():
    tech = {t: {"close": 100.0, "sma50": 95.0, "sma200": 90.0, "sma50_steigung": 1.0, "ret_126d": r, "ret_21d": 1.0,
                "ret_63d": r / 2} for t, r in [("AAA", 30.0), ("BBB", 5.0), ("CCC", -10.0)]}
    fund = {"AAA": {"grossMargins": 0.6, "forwardPE": 20, "numberOfAnalystOpinions": 10, "targetMeanPrice": 130,
                    "recommendationMean": 1.5}, "BBB": {}, "CCC": {"forwardPE": -5}}
    s = scoring.stocks(tech, fund, {"AAA": "Tech", "BBB": "Tech", "CCC": "Tech"}, 2.0)
    assert s["kennzahlen_score"].between(0, 100).all()
    assert s.loc["BBB", "fehlend"] > 0
    assert s.loc["AAA", "momentum"] > s.loc["CCC", "momentum"]
    assert s.loc["CCC", "bewertung"] < 50          # negativer Gewinn = 0 Punkte im Sektorvergleich


# ------------------------------------------------------------------ ledger

def _b(rows, start="2026-01-05"):
    idx = pd.bdate_range(start, periods=len(rows))
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


def test_simulate_limit_fill_then_target():
    bars = _b([[105, 106, 104, 105], [104, 104, 99, 100], [100, 103, 99.5, 102], [102, 112, 101, 111]])
    r = ledger.simulate(bars, "A", einstieg=100, stopp=95, ziel=110)
    assert r["fill_preis"] == 100 and r["exit_grund"] == "ziel" and r["exit_preis"] == 110


def test_simulate_fill_bar_only_stop():
    bars = _b([[101, 102, 94, 96]])                        # Fuellung und Stopp auf derselben Kerze
    r = ledger.simulate(bars, "A", einstieg=100, stopp=95, ziel=110)
    assert r["exit_grund"] == "stopp" and r["exit_preis"] == 95


def test_simulate_gap_down_fill_at_open():
    bars = _b([[98, 99, 97, 98], [98, 99, 97, 98]])
    r = ledger.simulate(bars, "A", einstieg=100, stopp=95, ziel=110, hold_max=1)
    assert r["fill_preis"] == 98 and r["exit_grund"] == "zeit"


def test_simulate_stop_before_target_same_bar():
    bars = _b([[101, 101, 99, 100], [100, 112, 94, 100]])
    r = ledger.simulate(bars, "A", einstieg=100, stopp=95, ziel=110)
    assert r["exit_grund"] == "stopp"


def test_simulate_not_filled_and_pending():
    far = _b([[110, 111, 109, 110]] * C.FILL_WINDOW)
    assert ledger.simulate(far, "A", 100, 95, 120)["exit_grund"] == "nicht_gefuellt"
    assert ledger.simulate(far.iloc[:3], "A", 100, 95, 120) is None


def test_simulate_breakout_stop_order():
    bars = _b([[100, 101, 99, 100], [103, 106, 102, 105], [105, 116, 104, 115]])
    r = ledger.simulate(bars, "B", einstieg=102, stopp=98, ziel=115)
    assert r["fill_preis"] == 103 and r["exit_grund"] == "ziel"


def test_ledger_append_dedupe_and_evaluate(tmp_path, monkeypatch):
    p = tmp_path / "ledger.csv"
    row = {"erstellt": "2026-01-02", "stand": "2026-01-02", "screener": "aktien", "version": "t", "status": "probe",
           "art": "szenario", "objekt": "AAA", "szenario": "A", "einstieg": 100.0, "stopp": 95.0, "ziel": 110.0}
    assert ledger.append([row], p) == 1
    assert ledger.append([row | {"stand": "2026-01-03"}], p) == 0        # offen -> kein Duplikat
    grp = {"erstellt": "2026-01-02", "stand": "2026-01-02", "screener": "aktien", "version": "t", "status": "probe",
           "art": "gruppe", "objekt": "KAUFEN", "horizont": 2, "titel": "AAA"}
    assert ledger.append([grp], p) == 1
    stock = pd.concat([_b([[100, 100, 100, 100]], "2026-01-02"),
                       _b([[104, 104, 99, 100], [100, 111, 99.5, 108], [108, 109, 107, 108]], "2026-01-05")])
    bench = pd.concat([_b([[50, 50, 50, 50]], "2026-01-02"), _b([[50, 51, 49, 51]] * 3, "2026-01-05")])
    n = ledger.evaluate({"AAA": stock, "SPY": bench}, "aktien", "SPY", p)
    assert n == 2
    df = ledger.read(p)
    sz = df[df["art"] == "szenario"].iloc[0]
    assert sz["exit_grund"] == "ziel"
    assert sz["ergebnis_r"] == pytest.approx(2 - 5e-4 * 100 / 5, rel=1e-3)
    g = df[df["art"] == "gruppe"].iloc[0]
    assert g["ergebnis_pct"] == pytest.approx(8.0) and g["bench_pct"] == pytest.approx(2.0)


def test_evaluate_no_lookahead(tmp_path):
    p = tmp_path / "ledger.csv"
    ledger.append([{"erstellt": "x", "stand": "2026-01-06", "screener": "aktien", "version": "t", "status": "probe",
                    "art": "szenario", "objekt": "AAA", "szenario": "A", "einstieg": 100.0, "stopp": 95.0,
                    "ziel": 110.0}], p)
    # Fuellung UND Ziel nur am/vor dem Stand -> darf nicht zaehlen
    d = _b([[104, 104, 99, 100], [100, 111, 99, 108]], "2026-01-05")
    ledger.evaluate({"AAA": d, "SPY": d}, "aktien", "SPY", p)
    assert ledger.read(p).iloc[0]["ausgewertet"] in (False, "False")


# ------------------------------------------------------------------ analyst-Validator

PACK = {"szenarien": {"A": {"einstieg": 148.8, "stopp": 136.14, "ziel": 177.2}, "B": None, "C": {"text": "x"}},
        "technik": {"close": 162.85}}


def _raw(**kw):
    base = {"sentiment": 1, "sentiment_grund": "ok", "news": [], "pro": ["a"], "contra": ["b"], "szenario": "A",
            "szenario_grund": "Einstieg bei 148,8 $", "ueberzeugung": "mittel", "hauptrisiko": "x"}
    return base | kw


def test_validator_accepts_pack_prices():
    out = analyst.validate(_raw(), PACK, analyst.allowed_prices_of(PACK))
    assert out["szenario"] == "A" and out["warnungen"] == []


def test_validator_flags_invented_price():
    out = analyst.validate(_raw(szenario_grund="Ziel 250 $"), PACK, analyst.allowed_prices_of(PACK))
    assert any("250" in w for w in out["warnungen"])


def test_validator_rejects_missing_scenario():
    out = analyst.validate(_raw(szenario="B"), PACK, analyst.allowed_prices_of(PACK))
    assert out["szenario"] == "C" and out["warnungen"]


def test_validator_clamps_sentiment_and_bad_json():
    assert analyst.validate(_raw(sentiment=7), PACK, set())["sentiment"] == 2
    with pytest.raises(ValueError):
        analyst.parse("keine Antwort")
    with pytest.raises(ValueError):
        analyst.validate(_raw(sentiment="viel"), PACK, set())


# ------------------------------------------------------------------ universe

def test_stock_universe_no_duplicates():
    u = universe.stocks()
    assert not u["ticker"].duplicated().any()
    assert {"NVDA", "AAPL", "BRK-B"} <= set(u["ticker"])


def test_validator_german_thousands_and_headline_numbers():
    pack = PACK | {"schlagzeilen": [{"titel": "Barclays raises target to $168 as bitcoin slides to 65,000"}]}
    allowed = analyst.allowed_prices_of(pack)
    out = analyst.validate(_raw(szenario_grund="Kursziel $168, Bitcoin bei 65.000 Dollar"), pack, allowed)
    assert out["warnungen"] == []
    assert analyst._num("65.000") == 65000 and analyst._num("170,41") == 170.41
