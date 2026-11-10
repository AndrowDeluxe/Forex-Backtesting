import pandas as pd

from fusion_lab.filters.zins_fx import ZinsFxFilter


def _data(jump_on=None):
    days = pd.bdate_range("2020-01-01", periods=40)
    rows = []
    for i, d in enumerate(days):
        ea = 1.0 + 0.01 * i  # EA-2y steigt stetig -> Spread steigt, EA hoeher verzinst
        if jump_on is not None and d >= jump_on:
            ea = -5.0  # Sprung ab dem Abfragetag darf nichts aendern
        rows += [{"key": "US.2y", "date": d, "value": 0.5}, {"key": "EA.2y", "date": d, "value": ea},
                 {"key": "JP.2y", "date": d, "value": 0.0}]
    return pd.DataFrame(rows), days


def test_directions():
    df, days = _data()
    f = ZinsFxFilter(lag=20, data=df)
    assert f.momentum_dir("EURUSD", days[30]) == 1
    assert f.carry_dir("EURUSD", days[30]) == 1
    assert f.carry_dir("USDJPY", days[30]) == 1  # JP tiefer verzinst -> USDJPY long
    assert f.momentum_dir("EURUSD", days[10]) == 0  # zu wenig Historie


def test_no_lookahead():
    df, days = _data()
    jumped, _ = _data(jump_on=days[30])
    a, b = ZinsFxFilter(20, df), ZinsFxFilter(20, jumped)
    assert a.momentum_dir("EURUSD", days[30]) == b.momentum_dir("EURUSD", days[30])
    assert a.carry_dir("EURUSD", days[30]) == b.carry_dir("EURUSD", days[30])


def test_tvc_fills_only_before_main_series():
    days = pd.bdate_range("2020-01-01", periods=5)
    df = pd.DataFrame([{"key": "AU.2y_tvc", "date": d, "value": 9.0} for d in days]
                      + [{"key": "AU.2y", "date": d, "value": 1.0} for d in days[3:]])
    s = ZinsFxFilter(data=df).wide["AU.2y"]
    assert s.tolist() == [9.0, 9.0, 9.0, 1.0, 1.0]


def test_state():
    assert ZinsFxFilter.state(1, "long") == "dafuer"
    assert ZinsFxFilter.state(-1, "long") == "dagegen"
    assert ZinsFxFilter.state(0, "short") == "neutral"
