import numpy as np
import pandas as pd

from fk_instant_funding.paper_bot import _append_forming_h4_bar
from mt5_gold_silver_divergenz.pipeline import ATR_LEN, _atr


def _frame(n=60, start="2026-11-01 00:00", base=4000.0):
    idx = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    rng = np.random.default_rng(0)
    close = base + rng.normal(0, 10, n).cumsum()
    return pd.DataFrame({"open": close, "high": close + 15, "low": close - 15,
                         "close": close, "volume": 1.0}, index=idx)


def test_appends_forming_bar_and_keeps_atr():
    xau, xag = _frame(), _frame(base=50.0)
    last = xau.index[-1]
    end = (last + pd.Timedelta(hours=5)).tz_localize(None)  # 1 h in die naechste Kerze
    x2, y2 = _append_forming_h4_bar(xau, xag, end)
    assert len(x2) == len(xau) + 1 and x2.index[-1] == last + pd.Timedelta(hours=4)
    assert y2.index[-1] == x2.index[-1]
    assert x2["open"].iloc[-1] == xau["close"].iloc[-1]
    assert abs(_atr(x2, ATR_LEN).iloc[-1] - _atr(xau, ATR_LEN).iloc[-1]) < 1e-9


def test_no_bar_outside_next_window():
    xau, xag = _frame(), _frame(base=50.0)
    last = xau.index[-1]
    for hours in (2, 9):  # Kerze laeuft noch / Wochenende bzw. Luecke
        end = (last + pd.Timedelta(hours=hours)).tz_localize(None)
        x2, _ = _append_forming_h4_bar(xau, xag, end)
        assert len(x2) == len(xau)
