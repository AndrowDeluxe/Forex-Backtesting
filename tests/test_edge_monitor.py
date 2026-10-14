import numpy as np
import pandas as pd

from edge_monitor import calibrate, signals, switch


def test_signals_causal():
    """Wert nach Trade k haengt nicht von spaeteren Trades ab."""
    rng = np.random.default_rng(1)
    r = rng.normal(0.3, 1.0, 200)
    r2 = r.copy(); r2[150:] = -5.0
    for s in signals.SIGNALS:
        a = signals.compute(s, r, 0.3, 1.0, 200)
        b = signals.compute(s, r2, 0.3, 1.0, 200)
        assert np.allclose(a[:150], b[:150], equal_nan=True), s


def test_cusum_known_values():
    # mu0=1, sd0=1 -> kref 0,5; r = 0 -> +0,5 je Schritt
    out = signals.cusum(np.zeros(4), 1.0, 1.0)
    assert np.allclose(out, [0.5, 1.0, 1.5, 2.0])


def test_sprt_step():
    # Schritt = ((r-mu0)^2 - r^2) / 2 sd^2 ; r=0, mu0=1 -> 0,5
    assert np.allclose(signals.sprt(np.zeros(3), 1.0, 1.0), [0.5, 1.0, 1.5])


def test_hysteresis():
    b = np.array([0, 3, 2.5, 1.6, 1.4, 3.1])
    st = switch.state_seq(b, thr=3.0, rel=1.5)
    assert st.tolist() == [False, True, True, True, False, True]
    assert switch.episodes_seq(b, 3.0, 1.5) == 2


def test_mask_uses_only_closed_trades():
    entry = pd.to_datetime(["2026-01-01 10:00", "2026-01-01 10:30", "2026-01-02 10:00"])
    exit_ = pd.to_datetime(["2026-01-01 12:00", "2026-01-01 11:00", "2026-01-02 12:00"])
    order = switch.close_order(exit_)
    assert order.tolist() == [1, 0, 2]
    states = np.array([True, False, False])          # Alarm nach dem 1. Schluss (11:00), weg nach dem 2.
    live = switch.mask_from_states(entry, exit_, states)
    # Trade 1 (10:30): nichts geschlossen -> live; Trade 2 (Folgetag): beide geschlossen, Alarm aus -> live
    assert live.tolist() == [True, True, True]
    states = np.array([False, True, True])
    assert switch.mask_from_states(entry, exit_, states).tolist() == [True, True, False]


def test_calibration_respects_budget():
    rng = np.random.default_rng(3)
    r = rng.normal(0.2, 1.0, 600)
    cfg = calibrate.thresholds(r, trades_per_year=100)
    thr, rel = cfg["signale"]["cusum"]["streng"]
    paths = rng.choice(r, size=(100, 500))
    eps = np.mean([switch.episodes_seq(signals.cusum(p, cfg["mu0"], cfg["sd0"]), thr, rel) for p in paths])
    assert eps <= 1.0 * 1.6   # Budget 1 je 5 Jahre (500 Trades), mit Schaetzrauschen
