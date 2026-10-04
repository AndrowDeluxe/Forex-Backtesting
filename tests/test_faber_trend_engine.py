"""Unit-Tests fuer faber_trend.engine (synthetische Kurse)."""
import numpy as np
import pandas as pd
import pytest

from faber_trend import engine as E


def _df(closes, start="2020-01-01", lows=None, opens=None):
    idx = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    o = pd.Series(opens if opens is not None else closes, index=idx, dtype=float)
    lo = pd.Series(lows if lows is not None else np.minimum(c, o), index=idx, dtype=float)
    hi = np.maximum(c, o)
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c})


def _setup(df, inst="SP500"):
    prep = E.prepare({inst: df})
    prep[inst]["df"]["atr"] = 1.0  # feste ATR, damit Stops deterministisch sind
    return prep


def _target_from(df, month, inst="SP500"):
    """Long-Ziel ab dem Monat `month` (Ausfuehrung am 1. Handelstag des Folgemonats)."""
    months = pd.period_range(df.index[0].to_period("M"), df.index[-1].to_period("M"))
    return pd.Series([(inst, 1) if m >= pd.Period(month) else (None, 0) for m in months], index=months)


def _run(prep, tg, stop, account=None, costs=None, risk=0.01):
    return E.run(prep, [E.Sleeve("s", tg)], stop, E.Sizing(risk_pct=risk),
                 costs or E.Costs(0, 0), account or E.Account("t", 100_000, False))


def test_sl_intraday_fill_at_stop():
    n = 80
    closes = [100.0] * n
    lows = [100.0] * n
    df = _df(closes, lows=lows)
    entry = pd.Timestamp("2020-02-03")  # 1. Handelstag Feb -> Signal Januar
    i = df.index.get_loc(entry)
    df.iloc[i + 3, df.columns.get_loc("low")] = 94.0  # unter SL 95
    res = _run(_setup(df), _target_from(df, "2020-01"), E.StopRule("pct", 0.05))
    t = res["trades"].iloc[0]
    assert t.reason == "sl" and t.exit_px == pytest.approx(95.0)
    assert t.r == pytest.approx(-1.0)


def test_gap_through_sl_fills_at_open():
    n = 80
    df = _df([100.0] * n)
    i = df.index.get_loc(pd.Timestamp("2020-02-03"))
    for c in ("open", "low", "close", "high"):
        df.iloc[i + 2, df.columns.get_loc(c)] = 90.0
    res = _run(_setup(df), _target_from(df, "2020-01"), E.StopRule("pct", 0.05))
    t = res["trades"].iloc[0]
    assert t.reason == "sl" and t.exit_px == pytest.approx(90.0)
    assert t.r == pytest.approx(-2.0)


def test_monthly_close_before_sl():
    df = _df([100.0] * 80)
    months = pd.period_range(df.index[0].to_period("M"), df.index[-1].to_period("M"))
    tg = pd.Series([("SP500", 1) if str(m) == "2020-01" else (None, 0) for m in months], index=months)
    res = _run(_setup(df), tg, E.StopRule("pct", 0.05))
    t = res["trades"].iloc[0]
    assert t.reason == "signal"
    assert t.exit_day == pd.Timestamp("2020-03-02")  # 1. Handelstag Maerz


def test_min_lot_rejection():
    df = _df([100.0] * 80)
    # GOLD: Kontrakt 100 -> 0,01 Lot = 1 Einheit = 100 Nominal; Risiko 1 % von 30 = 0,3
    res = _run(_setup(df, "GOLD"), _target_from(df, "2020-01", "GOLD"), E.StopRule("pct", 0.05),
               account=E.Account("ek", 30.0, True))
    assert res["skipped"] >= 1 and res["trades"].empty and res["open_at_end"] == 0


def test_weekend_swap_three_days():
    df = _df([100.0] * 80)
    res = _run(_setup(df), _target_from(df, "2020-01"), E.StopRule("pct", 0.05),
               costs=E.Costs(spread=0.0, swap_pa=0.365), risk=0.05)
    eq = res["equity"]
    # Nominal = 5 % Risiko / 5 % SL = 100 % von 100k; 0,1 %/Kalendertag
    fri = pd.Timestamp("2020-02-07")
    mon = pd.Timestamp("2020-02-10")
    tue = pd.Timestamp("2020-02-11")
    assert eq[fri] - eq[mon] == pytest.approx(3 * 100.0, rel=1e-3)
    assert eq[mon] - eq[tue] == pytest.approx(1 * 100.0, rel=1e-3)
