import re

import pandas as pd

from fusion_lab.macro_agent import fact_sheet, render
from fusion_lab.macro_agent.analytics import gates, profiles, state_machine


def _wide(values: dict[str, list[float]]) -> pd.DataFrame:
    n = len(next(iter(values.values())))
    return pd.DataFrame(values, index=pd.bdate_range("2026-10-01", periods=n))


def test_r_gate_follows_spread_change():
    w = _wide({"EA.2y": [2.0] * 5 + [2.1], "US.2y": [4.0] * 6})
    r = gates.rates_direction("EURUSD", w)
    assert r["dir"] == 1 and r["chg_bp"] == 10.0
    res = gates.evaluate("EURUSD", None, w, None, {})
    assert res["long"]["R"] == "PASS" and res["short"]["R"] == "FAIL"


def test_r_gate_equal_moves_are_no_signal():
    w = _wide({"EA.2y": [2.0] * 5 + [1.95], "US.2y": [4.0] * 5 + [3.95]})
    assert gates.rates_direction("EURUSD", w)["dir"] == 0


def test_missing_data_is_not_available():
    res = gates.evaluate("NZDUSD", None, _wide({"US.2y": [4.0] * 6}), None, {})
    assert res["long"]["R"] == res["long"]["P"] == res["long"]["B"] == res["long"]["F"] == "n.v."
    assert res["long"]["verfuegbar"] == 0


def test_f_gate_crowded_side_fails_and_cross_mirrors_quote():
    pos = {"EUR": {"cot_3y": 95.0}, "USD": {"cot_3y": 50.0}, "JPY": {"cot_3y": 5.0}}
    eurusd = gates.evaluate("EURUSD", None, _wide({"US.2y": [4.0] * 6}), None, pos)
    assert eurusd["long"]["F"] == "FAIL" and eurusd["short"]["F"] == "PASS"
    # Quote JPY ueberlaufen short -> long USDJPY (= JPY short) ist ueberlaufen
    usdjpy = gates.evaluate("USDJPY", None, _wide({"US.2y": [4.0] * 6}), None, pos)
    assert usdjpy["long"]["F"] == "FAIL" and usdjpy["short"]["F"] == "PASS"


def test_b_gate_uses_g8_difference():
    g8 = pd.Series({"GBP": 0.9, "JPY": 0.4})
    res = gates.evaluate("GBPJPY", None, _wide({"US.2y": [4.0] * 6}), g8, {})
    assert res["long"]["B"] == "PASS" and res["inputs"]["B"]["diff"] == 0.5


def test_state_machine_tail_needs_two():
    one = state_machine.evaluate({"vix": 30.0, "hy_spread": 3.0, "brent": 90.0})
    two = state_machine.evaluate({"vix": 30.0, "hy_spread": 3.6, "brent": 90.0})
    calm = state_machine.evaluate({"vix": 14.0, "hy_spread": 2.8, "brent": 80.0})
    assert one["state"] == "BASE" and two["state"] == "TAIL" and calm["state"] == "ALT"


def test_safe_haven_day():
    idx = pd.bdate_range("2026-11-02", periods=3)
    days = state_machine.safe_haven_days(pd.Series([100, 101, 100.5], idx), pd.Series([100, 98, 99], idx),
                                         pd.Series([20, 26, 22], idx))
    assert days == [idx[1].date().isoformat()]


def test_profile_ignores_values_after_as_of():
    long = pd.DataFrame({"key": "US.2y", "date": pd.to_datetime(["2026-11-05", "2026-11-06", "2026-11-09"]),
                         "value": [4.0, 4.1, 9.9]})
    long = long[long["date"] <= pd.Timestamp("2026-11-06")]
    p = profiles.country_profile(profiles.wide(long), "US", pd.Timestamp("2026-11-06"))
    assert p["2y"]["value"] == 4.1 and p["2y"]["chg_5d_bp"] is None


def test_flatten_skips_bools_and_text():
    reg = fact_sheet.flatten({"a": {"b": 1.5, "ok": True, "t": "x"}, "l": [{"v": 2}]})
    assert reg == {"a.b": 1.5, "l[0].v": 2}


def _mini_sheet() -> dict:
    gate = {"R": "PASS", "P": "FAIL", "F": "PASS", "pass": 2, "verfuegbar": 3}
    st = {"close": 1.12345, "date": "2026-11-09", "ret_5d_pct": 0.27, "ret_20d_pct": -0.56, "sma20": 1.12,
          "sma50": 1.11, "dist_sma20_pct": 0.22, "atr14": 0.00653}
    land = {"policy_rate": {"value": 3.88, "stale": False}, "2y": {"value": 4.51, "chg_5d_bp": -5.0},
            "cpi_yoy": {"value": 3.7, "stale": True}, "pricing": {"value": 0.68, "chg_5d_bp": 14.6}}
    card = {"carry": 0.74, "zins_momentum": 1.6, "preis_momentum": 0.52, "value": -0.45, "ueberraschung": 2.14,
            "score": 0.91, "rang": 1, "cot_3y": 18.9, "veto_long": False, "veto_short": False}
    sheet = {
        "stand": "2026-11-09", "erzeugt": "x",
        "zustand": {"state": "BASE", "state_week_ago": "BASE", "dollar_haven_days": [],
                    "tail": [{"name": "vix", "op": ">", "threshold": 28.0, "value": 25.64, "hit": False}],
                    "alt": [], "levels": {"dxy": 101.68, "spx": 7549.94, "gold": 4147.1, "brent": 92.31}},
        "regime": {"fehler": "x"}, "filter": {},
        "scorecard": {"tag": "2026-11-09", "waehrungen": {"USD": card}, "einsatz": "Kontext",
                      "test": {"lock": "x", "versuche": 8, "kandidat": "V3",
                               "is": {"V3": {"sharpe": -0.27, "t": -0.86}}, "oos": {"V3": {"sharpe": -0.21, "t": -0.65}}}},
        "taktisch": {"fed": {"effektiv": 3.88, "sitzungen": [{"sitzung": "2026-12-09", "bp": 28.2, "pct": 112.7,
                                                              "pct_vor_1w": 81.7, "bezahlt": True}]},
                     "notenbanken": {"GB": {"leitzins": 4.0, "leitzins_datum": "2026-11-05", "1y": 4.68,
                                            "gepreist_12m_bp": 68.5, "chg_1w_bp": -8.5}},
                     "rohstoffe": {"CAD": {"rohstoff": "brent", "kurs": 92.51, "ret_20d_pct": -15.79,
                                           "ret_60d_pct": -1.35, "trend": "faellt", "schwelle": 105.0,
                                           "abstand_pct": -11.9}}},
        "risiko": {"ideen": [{"markt": "USDCAD", "seite": "long", "diff": 1.26, "vol_pct": 4.8, "groesse_rel": 1.25}],
                   "buendel": {"netto": {"USD": 1.0}, "ueber_deckel": {}, "deckel": 1.5, "haupttreiber": "USD"},
                   "schwelle_diff": 0.75},
        "laender": {l: land for l in ["US", "EA", "GB", "JP", "CH", "AU", "CA", "NZ"]},
        "positionierung": {"EUR": {"net": -78559, "chg_1w": -6985, "cot_26w": 0.0, "cot_3y": 0.0, "date": "2026-11-06"}},
        "g8": {"GBP": 0.91, "AUD": -1.3}, "g8_stand": "2026-11-09",
        "maerkte": {m: {"kurs": st, "vol_20d_pct": 5.44, "gates": {"long": gate, "short": gate},
                        "scorecard": {"diff": -1.27}} for m in render.MARKETS},
        "kalender": {"referenz_utc": "x", "naechste_7t": [], "ueberraschungen_14t": []},
        "datenluecken": [],
    }
    sheet["register"] = fact_sheet.flatten(sheet)
    return sheet


def test_every_table_number_is_in_register():
    sheet = _mini_sheet()
    allowed = {render.fmt(v, d) for v in sheet["register"].values() for d in range(6)}
    md = render.markdown(sheet)
    number = re.compile(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$")
    for line in md.splitlines():
        if not line.startswith("| ") or line.startswith("| Rang") or "---" in line:
            continue
        for cell in line.strip("| ").split(" | ")[1:]:
            cell = cell.rstrip("*")
            if number.match(cell):
                assert cell in allowed, f"{cell} nicht im Register ({line})"
