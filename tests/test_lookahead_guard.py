"""Tests fuer den Vorgriff-Waechter (lookahead_guard).

Neben Grundfaellen die drei bekannten Vorgriffe als Regressionstests: der Waechter
muss sie fangen, die korrigierte Fassung muss durchgehen.
"""
import numpy as np
import pandas as pd
import pytest

from lookahead_guard import (LookaheadError, check_truncation, engine_selftest,
                             make_noise_ohlc)


@pytest.fixture
def ohlc():
    return make_noise_ohlc(600, seed=3)


# --- Grundfaelle -----------------------------------------------------------

def test_kausaler_indikator_geht_durch(ohlc):
    rep = check_truncation(lambda d: d["close"].rolling(20).mean(), ohlc, n_cuts=15)
    assert rep.ok and rep.verglichene_zeilen > 0


def test_shift_minus_eins_wird_gefangen(ohlc):
    with pytest.raises(LookaheadError):
        check_truncation(lambda d: d["close"].shift(-1) > d["close"], ohlc, n_cuts=10)


def test_zentriertes_fenster_wird_gefangen(ohlc):
    with pytest.raises(LookaheadError):
        check_truncation(lambda d: d["close"].rolling(5, center=True).mean(), ohlc, n_cuts=10)


def test_normierung_ueber_ganze_stichprobe_wird_gefangen(ohlc):
    z = lambda d: (d["close"] - d["close"].mean()) / d["close"].std()
    rep = check_truncation(z, ohlc, n_cuts=5, raise_on_fail=False)
    assert not rep.ok and "VORGRIFF" in str(rep)


def test_expandierendes_quantil_geht_durch(ohlc):
    f = lambda d: d["close"].pct_change().abs().expanding(50).quantile(0.8)
    assert check_truncation(f, ohlc, n_cuts=10).ok


# --- Fall 1: ASB-Friktion (echte Funktion) ---------------------------------

def test_corwin_schultz_datiert_auf_t_nutzt_t_plus_1(ohlc):
    from bond_yield_indicator.friction import corwin_schultz_spread
    with pytest.raises(LookaheadError):
        check_truncation(lambda d: corwin_schultz_spread(d["high"], d["low"]), ohlc, n_cuts=10)


def test_corwin_schultz_auf_letztes_volles_fenster_geht_durch(ohlc):
    from bond_yield_indicator.friction import corwin_schultz_spread
    f = lambda d: corwin_schultz_spread(d["high"], d["low"]).shift(1)
    assert check_truncation(f, ohlc, n_cuts=10).ok


# --- Fall 2: Lake-H4-Duplikate (echte Merge-Funktion) ----------------------

def _h4_m15(dupes: bool):
    """30 Tage = 180 H4-Kerzen. Wie im echten Fall (Lake, Juni-Sept.) traegt nur ein
    Teilfenster Duplikate: die letzten 100 Kerzen je eine Zusatzkerze +1 h. Dann ist der
    Modus der Abstaende 1 h (alter Code), das 75-%-Quantil aber 4 h (Fix vom 28.10.)."""
    m15_idx = pd.date_range("2026-07-01", periods=24 * 4 * 30, freq="15min")
    rng = np.random.default_rng(1)
    m15 = pd.DataFrame({"close": 100 + np.cumsum(rng.normal(0, 0.1, len(m15_idx)))}, index=m15_idx)
    h4 = m15["close"].resample("4h").last().to_frame()  # Stempel = Eroeffnung
    if dupes:
        extra = h4.iloc[-100:].copy()
        extra.index = extra.index + pd.Timedelta("1h")
        h4 = pd.concat([h4, extra]).sort_index()
    return {"m15": m15, "h4": h4}


def _merge_mit(bar_length):
    from gold_smc_htf_ltf.continuation import _merge_asof_shifted

    def fn(m15, h4):
        shift = bar_length(h4.index)
        vals = _merge_asof_shifted(m15.index, h4["close"], shift, "h4_close")
        return pd.Series(vals, index=m15.index, name="h4_close")
    return fn


def _modus_alt(index):
    diffs = pd.Series(index[1:] - index[:-1])
    return diffs.mode().iloc[0]


def test_alte_balkenlaenge_mit_duplikaten_wird_gefangen():
    with pytest.raises(LookaheadError):
        check_truncation(_merge_mit(_modus_alt), _h4_m15(dupes=True), n_cuts=20,
                         known_after={"m15": "15min", "h4": "4h"})


def test_neue_balkenlaenge_mit_duplikaten_geht_durch():
    from gold_smc_htf_ltf.continuation import _bar_length
    rep = check_truncation(_merge_mit(_bar_length), _h4_m15(dupes=True), n_cuts=20,
                           known_after={"m15": "15min", "h4": "4h"})
    assert rep.ok


# --- Fall 3: CTNL-Risikohalbierung (Trade-Liste) ---------------------------

def _trades(d: pd.DataFrame, nur_geschlossene: bool) -> pd.DataFrame:
    """Einstieg an jedem 7. Balken, Ausstieg 10 Balken spaeter (Trades ueberlappen).
    Risiko halbiert, wenn der letzte Vorgaenger verloren hat."""
    rows, c, idx = [], d["close"].to_numpy(), d.index
    for i in range(0, len(d), 7):
        j = i + 10
        offen = j >= len(d)
        rows.append({"entry_time": idx[i],
                     "exit_time": pd.NaT if offen else idx[j],
                     "r": np.nan if offen else float(np.sign(c[j] - c[i]))})
    t = pd.DataFrame(rows)
    risk = []
    for k, row in t.iterrows():
        vor = t.iloc[:k]
        if nur_geschlossene:
            vor = vor[vor["exit_time"] <= row["entry_time"]]
        letzte = vor["r"].iloc[-1] if len(vor) else np.nan
        risk.append(0.5 if letzte == -1 else 1.0)
    t["risk"] = risk
    return t


def test_halbierung_mit_offenen_vorgaengern_wird_gefangen(ohlc):
    with pytest.raises(LookaheadError):
        check_truncation(lambda d: _trades(d, nur_geschlossene=False), ohlc, n_cuts=25,
                         time_col="entry_time", key=["entry_time"], columns=["risk"])


def test_halbierung_nur_geschlossene_geht_durch(ohlc):
    rep = check_truncation(lambda d: _trades(d, nur_geschlossene=True), ohlc, n_cuts=25,
                           time_col="entry_time", key=["entry_time"], columns=["risk"])
    assert rep.ok


# --- Engine-Selbsttest -----------------------------------------------------

def _engine(cost: float, vorgriff: bool):
    def run(df, signal):
        o, c = df["open"].to_numpy(), df["close"].to_numpy()
        out = []
        for i in np.flatnonzero(signal.to_numpy()):
            if i + 1 >= len(df):
                continue
            ein = o[i] if vorgriff else o[i + 1]  # Vorgriff: fuellt auf dem Signal-Balken
            out.append(c[i + 1] / ein - 1 - cost)
        return out
    return run


def test_korrekte_engine_besteht():
    rep = engine_selftest(_engine(0.0005, vorgriff=False), cost=0.0005)
    assert rep.ok, str(rep)


def test_engine_mit_fuellung_vor_signal_faellt_durch():
    with pytest.raises(LookaheadError, match="signalbalken"):
        engine_selftest(_engine(0.0, vorgriff=True))


def test_engine_ohne_edge_erkennung_faellt_durch():
    blind = lambda df, s: list(np.random.default_rng(0).normal(0, 0.01, 200))
    rep = engine_selftest(blind, raise_on_fail=False)
    assert not rep.ergebnisse["eingepflanzt"]["ok"]
