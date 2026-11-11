import pandas as pd

from htf_daily_trade.twin_trade import day_target, leg_stop


def test_leg_stop_varianten():
    # long, Einstieg 1.10, Daily-Stop 1.08, ATR 0.01
    assert abs(leg_stop("SA", 1, 1.10, 1.08, 0.01) - 1.075) < 1e-12
    assert leg_stop("SB", 1, 1.10, 1.08, 0.01) == 1.08
    assert abs(leg_stop("SC", 1, 1.10, 1.08, 0.01) - 1.085) < 1e-12
    assert leg_stop("SB", 1, 1.07, 1.08, 0.01) is None          # Limit hinter dem Daily-Stop entfaellt
    assert abs(leg_stop("SA", -1, 1.10, 1.12, 0.01) - 1.125) < 1e-12


def test_tagesziel_rueckfall():
    x = pd.DataFrame({"High": [1.11, 1.12], "Low": [1.09, 1.10]})
    # Vortageshoch 1.11 liegt nur 0.01 ueber 1.10 bei Risiko 0.02 -> naechstes Fractal >= 1 R, sonst 3 R
    assert day_target(x, 1, 1, 1.10, 0.02, [1.115, 1.13]) == 1.13
    assert abs(day_target(x, 1, 1, 1.10, 0.02, []) - 1.16) < 1e-12
    assert day_target(x, 1, 1, 1.08, 0.02, []) == 1.11
