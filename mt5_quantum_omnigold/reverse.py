"""Regeln des Quantum OmniGold EA aus dem Verhalten herleiten (Schritt 3).

Jede Funktion prueft eine Regel gegen die Tester-Ausgaben und meldet die
Trefferquote. Kalibriert wird nur auf Uebereinstimmung mit MT5, nie auf
Gewinn. Voraussetzung: `python -m mt5_quantum_omnigold.data_mt5` (schreibt
mt5_trades.parquet) und das Log-Ereignis-Parquet (read_log).

Dukascopy-Kerzen sind ~4 % breiter als die MT5-Testdaten und liegen ~0,2 $
tiefer; Toleranzen sind entsprechend gewaehlt.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from mt5_quantum_omnigold.data import load_gold_m1
from mt5_quantum_omnigold.data_mt5 import LOG_DIR, TRADES, read_log

RESULTS = Path(__file__).parent / "results"
EVENTS = RESULTS / "log_events.parquet"

ATR_TF, ATR_N = "15min", 30       # iATR(M15, 30), einfacher Durchschnitt der True Range
DONCHIAN_TF, DONCHIAN_N = "15min", 72   # Einstieg: Ausbruch ueber Hoch/Tief der letzten ~18 h


def bars(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    return m1.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def atr(m1: pd.DataFrame, tf: str = ATR_TF, n: int = ATR_N) -> pd.Series:
    b = bars(m1, tf)
    pc = b.close.shift()
    return (np.maximum(b.high, pc) - np.minimum(b.low, pc)).rolling(n).mean()


def load_events(refresh: bool = False) -> pd.DataFrame:
    if EVENTS.exists() and not refresh:
        return pd.read_parquet(EVENTS)
    ev = read_log(LOG_DIR / "20261019.log")
    ev.to_parquet(EVENTS)
    return ev


def opens(ev: pd.DataFrame) -> pd.DataFrame:
    o = ev[ev.ev == "open"].copy()
    o["s"] = np.where(o.kind == "buy", 1, -1)
    return o.reset_index(drop=True)


def check_timezone(m1: pd.DataFrame, trades: pd.DataFrame) -> float:
    """Anteil der MT5-Einstiegspreise innerhalb der Dukascopy-M1-Kerze."""
    b = m1.reindex(trades.t_in.dt.floor("min"))
    p = trades.p_in.values
    d = np.where(p < b.low, b.low - p, np.where(p > b.high, p - b.high, 0))
    return float(np.mean(d <= 0.5))


def check_atr(m1: pd.DataFrame, ev: pd.DataFrame) -> dict:
    """Geloggte 'ATR current' gegen iATR(M15, 30). Erwartet: Verhaeltnis ~1,04 (Datenbreite)."""
    a = ev[(ev.ev == "atr") & (ev.t < m1.index.max())]
    s = atr(m1)
    v = s.values[s.index.get_indexer(a.t.dt.floor(ATR_TF), method="ffill") - 1]
    r = v / a.value.values
    x = a.value.values * ATR_N * 100
    return dict(ratio_median=float(np.nanmedian(r)), ratio_iqr=np.nanpercentile(r, [25, 75]).round(3).tolist(),
                cent_sums=float(np.mean(np.abs(x - np.round(x)) < 0.02)))


def check_lines(m1: pd.DataFrame, ev: pd.DataFrame) -> dict:
    """res/support-Neuberechnung: nur wenn die gerade geschlossene M15-Kerze ein neues Hoch/Tief macht."""
    b = bars(m1, "15min")
    L = ev[(ev.ev == "line") & (ev.t < m1.index.max())]
    i = b.index.get_indexer(L.t.dt.floor("15min"))
    r = L.kind.eq("res").values
    h1, l1 = b.high.values[i - 1], b.low.values[i - 1]
    mh, ml = b.high.rolling(4).max().values[i - 1], b.low.rolling(4).min().values[i - 1]
    return dict(new_extreme=float(np.mean(np.where(r, h1 == mh, l1 == ml))),
                offset_median=float(np.median(np.where(r, L.value.values - h1, L.value.values - l1))))


def check_entries(m1: pd.DataFrame, ev: pd.DataFrame, tf: str = DONCHIAN_TF, n: int = DONCHIAN_N) -> float:
    """Einstieg = Bid erreicht Hoch (Buy) bzw. Tief (Sell) der letzten n abgeschlossenen Kerzen."""
    o = opens(ev)
    o = o[o.t < m1.index.max()]
    b = bars(m1, tf)
    i = b.index.get_indexer(o.t, method="ffill")
    hi, lo = b.high.rolling(n).max().values[i - 1], b.low.rolling(n).min().values[i - 1]
    return float(np.mean(np.abs((o.bid.values - np.where(o.s > 0, hi, lo)) * o.s) < 0.4))


def check_sl_tp(ev: pd.DataFrame) -> dict:
    """SL/TP beim Einstieg: Abstand X zu einem Fenster-Extrem; SL = min(X + ~0,9, 30), TP = min(X, 40).

    Gemessen ab Bid: TP-Abstand X, SL-Abstand X + Puffer. Gruppen nach SL-Abstand.
    """
    o = opens(ev)
    sld = np.where(o.s > 0, o.bid - o.sl, o.sl - o.ask)
    tpb = (o.tp - o.bid) * o.s
    small = sld < 29.9
    return dict(n=len(o), sl_eq_30=float(np.mean(np.abs(sld - 30) < 0.3)), sl_lt_30=float(small.mean()),
                buffer_median=float(np.median(sld[small] - tpb[small])),
                tp_capped_40=float(np.mean(tpb > 39.5)))


if __name__ == "__main__":
    m1 = load_gold_m1()
    ev = load_events()
    tr = pd.read_parquet(TRADES)
    print("Zeitzone EET/EU-Sommerzeit, Einstiege in M1-Kerze:", round(check_timezone(m1, tr), 3))
    print("ATR iATR(M15,30):", check_atr(m1, ev))
    print("Linien:", check_lines(m1, ev))
    print(f"Einstieg Donchian {DONCHIAN_TF} x {DONCHIAN_N}:", round(check_entries(m1, ev), 3))
    print("SL/TP:", check_sl_tp(ev))
