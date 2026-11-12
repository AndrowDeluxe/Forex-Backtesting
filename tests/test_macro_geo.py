"""Makro-Agent v3: Geopolitik-Daten, News-Einordnung, Earnings, Exposure-Matrix, Ereignisstudie."""

import io

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import geo_framework as g
from fusion_lab.macro_agent import news_digest
from fusion_lab.macro_data import earnings, geo
from scripts.research_geo_events import spikes


def test_parse_gpr_skips_label_rows():
    df = pd.DataFrame({"DAY": [20261101, 20261102, "x"], "GPRD": [86.2, 113.9, None],
                       "GPRD_ACT": [50.0, 60.0, None], "GPRD_THREAT": [70.0, 80.0, None]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    out = geo.parse_gpr(buf.getvalue())
    gpr = out[out["key"] == "MKT.gpr"].set_index("date")["value"]
    assert gpr[pd.Timestamp("2026-11-02")] == 113.9
    assert set(out["key"]) == {"MKT.gpr", "MKT.gpr_acts", "MKT.gpr_threats"}


def test_parse_gdelt_daily_series():
    payload = {"timeline": [{"data": [{"date": "20260228T000000Z", "value": 1.5},
                                      {"date": "20260227T000000Z", "value": 0.2}]}]}
    s = geo.parse_gdelt(payload)
    assert list(s.index) == [pd.Timestamp("2026-02-27"), pd.Timestamp("2026-02-28")]
    assert s.iloc[-1] == 1.5


RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Oil rises as Hormuz attacks continue - Reuters</title><source>Reuters</source>
<pubDate>Wed, 11 Nov 2026 08:00:00 GMT</pubDate><link>https://x/1</link></item>
<item><title>Iran talks resume - BBC</title><source>BBC</source>
<pubDate>Wed, 11 Nov 2026 10:00:00 GMT</pubDate><link>https://x/2</link></item>
</channel></rss>"""


def test_parse_rss_strips_source_and_sorts_newest_first():
    items = geo.parse_rss(RSS)
    assert items[0]["titel"] == "Iran talks resume" and items[0]["quelle"] == "BBC"
    assert items[1]["titel"] == "Oil rises as Hormuz attacks continue"
    assert geo.count_rss(RSS) == 2


def test_news_parse_drops_unknown_theme_and_bad_label():
    text = 'Antwort: [{"thema": "iran_hormuz", "lage": "eskalation", "kernaussage": "x", "quellen": ["BBC"]},' \
           ' {"thema": "mars", "lage": "eskalation"}, {"thema": "zoelle_trump", "lage": "panik"}]'
    out = news_digest.parse(text, ["iran_hormuz", "zoelle_trump"])
    assert list(out) == ["iran_hormuz"] and out["iran_hormuz"]["lage"] == "eskalation"


def test_earnings_summary_next_and_last():
    idx = pd.DatetimeIndex(["2026-11-17 16:00", "2026-08-26 16:00", "2026-05-20 16:00"]).tz_localize("America/New_York")
    d = pd.DataFrame({"EPS Estimate": [2.47, 2.09, 1.77], "Reported EPS": [np.nan, 2.22, 1.70],
                      "Surprise(%)": [np.nan, 6.16, -3.9]}, index=idx)
    s = earnings.summarize("NVDA", d, pd.Timestamp("2026-11-12"))
    assert s["naechster_termin"] == "2026-11-17" and s["erwartung_eps"] == 2.47
    assert s["letzter_termin"] == "2026-08-26" and s["letzte_ueberraschung_pct"] == 6.2
    assert s["beats_letzte_4"] == 1


def test_ols_recovers_slope():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=500))
    y = -0.5 * x + rng.normal(scale=0.1, size=500)
    beta, t, n = g.ols(y, x)
    assert abs(beta + 0.5) < 0.02 and t < -50 and n == 500


def test_status_rules():
    assert g.status(3, 3, 0.5, 1, 1, 1) == "belegt"
    assert g.status(3, 3, -1.5, 1, 1, -1) == "gekippt"
    assert g.status(0.5, 1, 2.5, 1, -1, 1) == "regime"
    assert g.status(3, -3, 0.5, 1, -1, 1) == "schwach"  # IS und OOS widersprechen sich


def test_weekly_changes_units():
    days = pd.bdate_range("2026-01-05", periods=15)
    d = pd.DataFrame({"gold": np.linspace(100, 110, 15), "real_10y": np.linspace(2.0, 2.3, 15),
                      "brent": 80.0, "dxy": 100.0, "us_2y": 4.0, "fed_funds": 3.5}, index=days)
    w = g.weekly_changes(d)
    assert abs(w["T.realzins"].dropna().iloc[0] - 10.71) < 0.1  # 5 Tage * 0,3/14 % = 0,107 % = 10,7 bp
    assert (w["regime"].iloc[1:] == "anhebungen").all()


def test_spikes_first_of_wave_only():
    idx = pd.date_range("2026-01-01", periods=30)
    gpr = pd.Series(100.0, index=idx)
    gpr.iloc[[5, 6, 7, 20]] = [200, 220, 210, 250]
    ev = spikes(gpr, 150)
    assert list(ev) == [idx[5], idx[20]]
