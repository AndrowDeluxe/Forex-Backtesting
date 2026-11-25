"""Makro-Agent Fact Sheet v4 (24.11.2026): Liquiditaet, Zinskurve, Marktverfassung, Carry/Vol, Trendfolger."""

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import manifest, render
from fusion_lab.macro_agent.analytics import plumbing, positioning_value
from fusion_lab.macro_data import sources


def _wide(cols: dict[str, pd.Series]) -> pd.DataFrame:
    return pd.DataFrame(cols).sort_index()


def test_net_liquidity_units_and_alignment():
    weeks = pd.date_range("2026-01-07", periods=20, freq="W-WED")
    days = pd.bdate_range("2026-01-01", "2026-05-30")
    w = _wide({"US.fed_assets": pd.Series(6_700_000.0, index=weeks),      # Mio. USD
               "US.tga": pd.Series(900_000.0, index=weeks),
               "US.rrp": pd.Series(5.0, index=days)})                     # Mrd. USD, taeglich
    net = plumbing.net_liquidity(w)
    assert len(net) == 20 and abs(net.iloc[-1] - (6700 - 900 - 5)) < 1e-9


def test_liquidity_reading_and_funding_stress():
    weeks = pd.date_range("2026-01-07", periods=20, freq="W-WED")
    days = pd.bdate_range("2026-01-01", periods=60)
    assets = pd.Series(np.linspace(6_500_000, 6_800_000, 20), index=weeks)
    w = _wide({"US.fed_assets": assets, "US.tga": pd.Series(800_000.0, index=weeks),
               "US.rrp": pd.Series(0.0, index=days), "US.sofr": pd.Series(4.00, index=days),
               "US.iorb": pd.Series(3.90, index=days)})
    out = plumbing.liquidity(w)
    assert out["lesart"] == "Liquidität steigt" and out["funding"].startswith("angespannt")
    assert abs(out["sofr_iorb_bp"] - 10.0) < 1e-9


def test_curve_shapes():
    assert plumbing.curve_shape(-20, -5) == "Bull-Steepener"
    assert plumbing.curve_shape(2, 15) == "Bear-Steepener"
    assert plumbing.curve_shape(15, 3) == "Bear-Flattener"
    assert plumbing.curve_shape(-1, -12) == "Bull-Flattener"
    assert plumbing.curve_shape(-10, -11) == "parallel"
    assert plumbing.curve_shape(None, 3) == "n.v."


def test_internals_inverted_vix_and_positive_stock_bond_corr():
    days = pd.bdate_range("2026-01-01", periods=120)
    rng = np.random.default_rng(3)
    common = rng.normal(0, 0.01, 120)
    spy = pd.Series(np.exp(np.cumsum(common)), index=days)
    tlt = pd.Series(np.exp(np.cumsum(common + rng.normal(0, 0.002, 120))), index=days)  # laufen gleich
    w = _wide({"MKT.vix_yf": pd.Series(30.0, index=days), "MKT.vix3m": pd.Series(25.0, index=days),
               "MKT.vix9d": pd.Series(33.0, index=days), "MKT.spy": spy, "MKT.tlt": tlt, "MKT.rsp": spy})
    out = plumbing.internals(w)
    assert out["vix_struktur"].startswith("invertiert")
    assert out["aktien_anleihen_korr"] > 0.9 and out["aktien_anleihen_lesart"].startswith("Anleihen sichern nicht")
    assert out["breite_chg_20t_pct"] == 0.0


def test_carry_vol_sign_and_order():
    days = pd.bdate_range("2026-01-01", periods=40)
    rng = np.random.default_rng(5)
    prices = {m: pd.DataFrame({"Close": np.exp(np.cumsum(rng.normal(0, s, 40)))}, index=days)
              for m, s in (("AUDJPY", 0.004), ("EURUSD", 0.004))}
    w = _wide({"AU.2y": pd.Series(3.5, index=days), "JP.2y": pd.Series(0.5, index=days),
               "EA.2y": pd.Series(2.0, index=days), "US.2y": pd.Series(3.5, index=days)})
    rows = positioning_value.carry_vol(prices, w)
    assert [r["markt"] for r in rows] == ["AUDJPY", "EURUSD"]
    assert rows[0]["carry_pct"] == 3.0 and rows[1]["carry_pct"] == -1.5


def test_trend_signal_and_flip_level():
    days = pd.bdate_range("2025-01-01", periods=300)
    up = pd.Series(np.linspace(100, 130, 300), index=days)
    s = positioning_value.trend_signal(up)
    assert s["signal"] == 1.0 and s["naechste_wende"] == "1M" and s["abstand_pct"] < 0
    assert positioning_value.trend_signal(up.iloc[:200]) is None


def test_acm_parser_and_brent_ticker():
    df = pd.DataFrame({"DATE": ["20-Nov-2026", "23-Nov-2026"], "ACMTP10": [0.71, 0.66], "ACMRNY10": [4.24, 4.29]})
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as xw:
        df.to_excel(xw, sheet_name="ACM Daily", index=False)
    out = sources.parse_acm(buf.getvalue())
    assert set(out["key"]) == {"US.term_premium_10y", "US.expected_10y"} and len(out) == 4
    assert sources.brent_contract(pd.Period("2027-01", "M"), 6) == "BZN27.NYM"


def test_renumber_and_asof_catches_new_dates():
    lines = ["## 4. A", "x", "## 5. B", "## 5. C", "## 13. D"]
    assert [l for l in render.renumber(lines) if l.startswith("##")] == ["## 1. A", "## 2. B", "## 3. C", "## 4. D"]
    sheet = {"desk": {"liquiditaet": {"datum": "2026-11-30"}}}
    assert manifest.asof_violations(sheet, pd.Timestamp("2026-11-24"))


def test_event_weights_regime_and_no_lookahead():
    """Termin-Gewicht CPI/NFP aus der 2J-Reaktion (26.11.): CPI-Termine bewegen die Rendite -> CPI dominiert;
    ein Termin nach dem Stichtag zaehlt nicht."""
    import numpy as np
    import pandas as pd
    from fusion_lab.macro_agent.analytics import event_weights as ew

    rng = np.random.default_rng(1)
    days = pd.bdate_range("2022-01-03", "2026-11-25")
    rows, dy = [], pd.Series(0.0, index=days)
    for i, mo in enumerate(pd.date_range("2022-01-01", "2026-12-01", freq="MS")):
        for name, off, beta in (("CPI m/m", 9, 8.0), ("Core CPI m/m", 9, 8.0), ("Non-Farm Employment Change", 3, 1.0)):
            d = days[days >= mo + pd.Timedelta(days=off)][0] if (days >= mo + pd.Timedelta(days=off)).any() else None
            if d is None:
                continue
            z = rng.normal()
            unit = "K" if "Farm" in name else "%"
            rows.append({"currency": "USD", "name": name, "time": pd.Timestamp(d, tz="UTC") + pd.Timedelta(hours=13),
                         "actual": f"{0.2 + 0.1 * z:.2f}{unit}", "forecast": f"0.20{unit}"})
            dy[d] += beta * z
    ff = pd.DataFrame(rows)
    macro_w = pd.DataFrame({"US.2y": 4 + dy.cumsum() / 100})
    w = ew.weights(macro_w, pd.Timestamp("2026-11-25"), ff)
    assert w["anteil_cpi"] >= 0.6 and w["regime"].startswith("Inflation")
    assert w["termine"]["CPI"]["letzter"] <= "2026-11-25"
    assert ew.tag("CPI m/m", "USD", w).startswith("CPI-Gewicht")
    assert ew.tag("ADP Non-Farm Employment Change", "USD", w) is None
