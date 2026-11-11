import calendar as cal

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import factors, fed_meetings, risk, tactical
from fusion_lab.macro_agent.analytics import state_machine
from fusion_lab.macro_data import calendar_values, sources


def test_calendar_policy_rates_and_parsing():
    ev = pd.DataFrame({"currency": ["GBP", "JPY", "USD", "AUD"],
                       "title": ["Official Bank Rate", "BOJ Policy Rate", "Federal Funds Rate", "Retail Sales m/m"],
                       "actual": ["4.00%", "<1.25%", "4.00%", "0.3%"],
                       "event_time": pd.to_datetime(["2026-11-05 12:00", "2026-10-30 03:02", "2026-10-28 18:00",
                                                     "2026-11-04 00:30"])})
    df = calendar_values.from_events(ev).set_index("key")
    assert df.loc["GB.policy_rate@cal", "value"] == 4.0
    assert df.loc["JP.policy_rate@cal", "value"] == 1.25
    assert "US.policy_rate@cal" not in df.index  # Kalender meldet die Obergrenze, BIS die Mitte
    assert len(df) == 2


def test_extend_only_after_main_and_alias():
    long = pd.DataFrame({"key": ["GB.policy_rate", "GB.policy_rate@cal", "GB.policy_rate@cal",
                                 "EA.policy_rate", "EA.ecb_deposit"],
                         "date": pd.to_datetime(["2026-11-02", "2026-09-17", "2026-11-05", "2026-11-03", "2026-11-10"]),
                         "value": [3.75, 3.75, 4.0, 2.5, 2.5]})
    out = calendar_values.extend(long)
    gb = out[out["key"] == "GB.policy_rate"].set_index("date")["value"]
    assert gb.index.max() == pd.Timestamp("2026-11-05") and gb.iloc[-1] == 4.0
    assert pd.Timestamp("2026-09-17") not in gb.index  # aelterer Ersatz ueberschreibt die Hauptreihe nicht
    assert out[out["key"] == "EA.policy_rate"]["date"].max() == pd.Timestamp("2026-11-10")
    assert not out["key"].str.contains("@").any()


def test_fed_meeting_probability_matches_hand_calc():
    start, d = 3.875, pd.Timestamp("2026-12-09")
    f = d.day / cal.monthrange(d.year, d.month)[1]
    avg_dec = f * start + (1 - f) * (start + 0.25)  # genau ein Schritt gepreist
    path = fed_meetings.meeting_path({"2026-11": start, "2026-12": avg_dec}, start, pd.Timestamp("2026-11-11"))
    assert len(path) == 1 and abs(path[0]["pct"] - 100.0) < 0.1 and path[0]["bezahlt"]


def test_xs_z_needs_four_lands():
    raw = pd.DataFrame({"US": [1.0, 1.0], "EA": [2.0, np.nan], "GB": [3.0, np.nan], "JP": [4.0, 2.0]})
    z = factors.xs_z(raw)
    assert abs(z.iloc[0].mean()) < 1e-9 and z.iloc[1].isna().all()


def test_month_end_weights_veto_blocks_side():
    days = pd.bdate_range("2026-01-26", "2026-01-30")
    score = pd.DataFrame([[2.0, 1.5, 0.5, 0.0, -0.5, -1.0, -1.5, -2.0]] * len(days), index=days,
                         columns=factors.LANDS)
    veto_long = pd.DataFrame(False, index=days, columns=factors.LANDS)
    veto_long["US"] = True
    w = factors.month_end_weights({"score": score, "veto_long": veto_long, "veto_short": ~veto_long & False}, 2)
    row = w.iloc[-1]
    assert row["US"] == 0.0 and row["EA"] == 0.5 and row["NZ"] == -0.5 and row["CA"] == -0.5


def test_bundle_flags_over_cap():
    ideas = [{"markt": "USDCHF", "seite": "long"}, {"markt": "USDCAD", "seite": "long"},
             {"markt": "EURUSD", "seite": "short"}]
    b = risk.bundle(ideas)
    assert b["netto"]["USD"] == 3.0 and "USD" in b["ueber_deckel"] and b["haupttreiber"] == "USD"


def test_ideas_skip_veto_and_small_diff():
    pairs = {"USDCAD": {"diff": 1.2, "veto_long": False, "veto_short": False},
             "AUDUSD": {"diff": -1.0, "veto_long": False, "veto_short": True},
             "EURGBP": {"diff": 0.3, "veto_long": False, "veto_short": False}}
    out = risk.ideas(pairs, {"USDCAD": 5.0})
    assert [i["markt"] for i in out] == ["USDCAD"] and out[0]["groesse_rel"] == 1.0


def test_stress_index_alone_triggers_tail():
    assert state_machine.evaluate({"vix": 15, "hy_spread": 3.0, "brent": 80, "stlfsi": 1.2})["state"] == "TAIL"
    assert state_machine.evaluate({"vix": 15, "hy_spread": 2.9, "brent": 80, "stlfsi": 0.0})["state"] == "ALT"


def test_commodity_switch_distance():
    idx = pd.bdate_range("2026-08-01", periods=70)
    w = pd.DataFrame({"MKT.brent": np.linspace(110, 92.4, 70)}, index=idx)
    node = tactical.commodities(w)["CAD"]
    assert node["schwelle"] == 105.0 and node["abstand_pct"] < 0 and node["trend"] == "faellt"


def test_parse_snb_core_takes_k1():
    text = ('"CubeId";"plkoprinfla"\n"PublishingDate";"2026-10-21 09:00"\n\n"Date";"D0";"Value"\n'
            '"2026-09";"KGM";"0.62"\n"2026-09";"K1";"0.5"\n')
    df = sources.parse_snb_core(text)
    assert df["key"].tolist() == ["CH.core_yoy@snb"] and df["value"].tolist() == [0.5]
