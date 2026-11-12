"""Makro-Agent v3 Phase 3: Dollar-Faktor, Unabhaengigkeit, Forecast-Ledger, As-of-Pruefung."""

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import ledger, manifest
from fusion_lab.macro_agent.analytics import dollar_factor, overlap


def _prices(n=80, seed=1):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2026-06-01", periods=n)
    usd = rng.normal(0, 0.005, n)
    out = {}
    for p in dollar_factor.USD_PAIRS:
        sign = 1.0 if p.startswith("USD") else -1.0
        r = sign * usd + rng.normal(0, 0.001, n)
        out[p] = pd.DataFrame({"Close": np.exp(np.cumsum(r))}, index=days)
    out["EURGBP"] = pd.DataFrame({"Close": np.exp(np.cumsum(rng.normal(0, 0.004, n)))}, index=days)
    return out


def test_dollar_factor_explains_usd_pairs_not_crosses():
    prices = _prices()
    f = dollar_factor.usd_factor(prices)
    d = dollar_factor.decompose(prices, f)
    assert d["USDJPY"]["beta"] > 0.8 and d["EURUSD"]["beta"] < -0.8
    assert d["USDJPY"]["dollar_anteil_pct"] > 80 and d["EURGBP"]["dollar_anteil_pct"] < 20


def test_three_usd_longs_are_one_bet():
    prices = _prices()
    d = dollar_factor.decompose(prices, dollar_factor.usd_factor(prices))
    ideas = [{"markt": m, "seite": "long"} for m in ("USDJPY", "USDCHF", "USDCAD")]
    b = dollar_factor.idea_bundle(prices, ideas, d)
    assert b["n_eff"] < 1.3 and b["dollar_netto"] > 2.5


def test_n_eff_counts_correlated_reasons_once():
    corr = pd.DataFrame([[1, 1, 0], [1, 1, 0], [0, 0, 1]], index=list("abc"), columns=list("abc"), dtype=float)
    r = overlap.reasons({"a": 1.0, "b": 1.0, "c": 1.0}, "long", corr)
    assert r["anzahl"] == 3 and abs(r["n_eff"] - 9 / 5) < 1e-9  # (3)^2 / (2^2 + 1)
    r = overlap.reasons({"a": 1.0, "b": -1.0, "c": None}, "short", corr)
    assert r["gruende"] == ["b"] and r["n_eff"] == 1.0


def _sheet():
    return {"stand": "2026-11-12", "risiko": {"ideen": [{"markt": "USDJPY", "seite": "long", "diff": 0.9}]},
            "geopolitik": {"themen": [{"thema": "iran_hormuz", "lage": "eskalation", "kernaussage": "x"},
                                      {"thema": "zoelle_trump", "lage": "unverändert", "kernaussage": "y"}]}}


def test_ledger_append_once_and_evaluate(tmp_path):
    path = tmp_path / "ledger.csv"
    assert ledger.append(_sheet(), path) == 3  # Idee 5T + 20T, Iran 5T; "unveraendert" zaehlt nicht
    assert ledger.append(_sheet(), path) == 0  # zweiter Lauf am selben Tag aendert nichts
    days = pd.bdate_range("2026-11-10", "2026-12-15")
    hist = pd.DataFrame({"USDJPY": np.linspace(150, 160, len(days)), "brent": np.linspace(95, 90, len(days))},
                        index=days)
    assert ledger.evaluate(hist, pd.Timestamp("2026-11-20"), path) == 2  # nur die 5-Tage-Eintraege
    s = ledger.summary(path)
    assert s["je_art"]["idee_5t"]["trefferquote_pct"] == 100
    assert s["je_art"]["thema_5t"]["trefferquote_pct"] == 0  # Eskalation, Brent fiel


def test_asof_violation_detected_but_future_dates_allowed():
    sheet = {"a": {"datum": "2026-11-13"}, "b": {"naechster_termin": "2027-01-27"}, "c": [{"stand": "2026-11-12"}]}
    v = manifest.asof_violations(sheet, pd.Timestamp("2026-11-12"))
    assert v == ["a.datum = 2026-11-13"]
