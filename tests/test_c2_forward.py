import pandas as pd

from htf_daily_trade.c2_forward import _limit_fill, meldungen
from htf_daily_trade.forward_data import daily_from_intraday


def _bars(lows, highs, opens=None):
    n = len(lows)
    return pd.DataFrame({"Open": opens or [1.0] * n, "High": highs, "Low": lows, "Close": [1.0] * n})


def test_limit_fill_within_three_days():
    x = _bars([1.0, 0.99, 0.95, 0.9, 0.8], [1.1] * 5)
    assert _limit_fill(x, "long", 1, 0.96) == (2, 0.96)
    assert _limit_fill(x, "long", 1, 0.85) == (None, None)  # Tag 4 liegt ausserhalb von 3 Tagen


def test_limit_fill_gap_takes_open():
    x = _bars([1.0, 0.9], [1.1, 1.0], opens=[1.0, 0.92])
    assert _limit_fill(x, "long", 1, 0.95) == (1, 0.92)


def _row(status, im_test=True):
    return {"markt": "EURUSD", "seite": "long", "signal_tag": "2026-11-12", "limit": 1.1, "stop": 1.09,
            "einstieg": 1.1, "r": 1.5, "status": status, "im_test": im_test}


def test_meldungen_nur_bei_statuswechsel_im_test():
    alt = pd.DataFrame([_row("wartet")])
    assert meldungen(pd.DataFrame([_row("wartet")]), alt) == []
    assert meldungen(pd.DataFrame([_row("offen")]), alt)[0].startswith("▶️")
    assert meldungen(pd.DataFrame([_row("wartet", im_test=False)]), None) == []
    assert meldungen(pd.DataFrame([_row("verfallen")]), alt)[0].startswith("⌛")


def test_daily_only_complete_days():
    idx = pd.date_range("2026-11-09 00:00", "2026-11-10 12:00", freq="1h", tz="UTC")
    b = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=idx)
    d = daily_from_intraday(b, today=pd.Timestamp("2026-11-11"))
    assert list(d.index) == [pd.Timestamp("2026-11-09")]  # 10.11. hat noch keine Folge-Bars
