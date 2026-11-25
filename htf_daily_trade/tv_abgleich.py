"""Abgleich indikatoren.py gegen TradingView-CSV-Exporte (FXCM-Kurse, tv_referenz/).

Rechnet alle Indikatoren auf den OHLC-Werten des Exports selbst und vergleicht mit den
geplotteten Spalten. Aufwaermphase wird uebersprungen.
Aufruf: python htf_daily_trade/tv_abgleich.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent))
import indikatoren as ind

REF = Path(__file__).parent / "tv_referenz"


def lade(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)  # doppelte Spaltennamen -> Upper.1, Lower.1, Plot.1 ...
    df["time"] = pd.to_datetime(df["time"], unit="s", errors="coerce") \
        if np.issubdtype(df["time"].dtype, np.number) else pd.to_datetime(df["time"], utc=True)
    return df.set_index("time")


def vergleich(name, ours, tv, skip, skala=1.0):
    a = pd.Series(np.asarray(ours, float), index=tv.index).iloc[skip:]
    b = tv.astype(float).iloc[skip:]
    m = a.notna() & b.notna()
    if m.sum() == 0:
        return f"  {name:<22} keine Werte"
    d = (a[m] - b[m]).abs() / skala
    return f"  {name:<22} n={m.sum():5d}  mittel={d.mean():.5f}  max={d.max():.5f}"


def pruefe(p: Path):
    df = lade(p)
    c = df["close"]
    print(f"\n=== {p.name}  ({len(df)} Kerzen, {df.index[0]} .. {df.index[-1]})")
    px = c.mean() / 100  # 1 % des Preises als Skala fuer Preis-Indikatoren
    r = ind.rsi_mit_ma(c)
    print(vergleich("RSI", r["rsi"], df["RSI"], 100))
    print(vergleich("RSI-MA", r["rsi_ma"], df["RSI-based MA"], 100))
    ml = ind.rsi_multi_length(c)
    print(vergleich("ML Mittel", ml["rsi_ml"], df["Average Multi Length RSI"], 100))
    print(vergleich("ML Upper", ml["rsi_ml_upper"], df["Upper Channel"], 300))
    print(vergleich("ML Lower", ml["rsi_ml_lower"], df["Lower Channel"], 300))
    print(vergleich("ML OB-Flaeche", ml["rsi_ml_ob_area"], df["Overbought Area"], 100))
    print(vergleich("ML OS-Flaeche(100-x)", 100 - ml["rsi_ml_os_area"], df["Oversold Area"], 100))
    print(vergleich("ATR (% Preis)", ind.atr(df), df["ATR"], 100, px))
    for lab, src, n, k in [("20/close/2", c, 20, 2.0),
                           ("34/hl2/2.5", (df["high"] + df["low"]) / 2, 34, 2.5)]:
        bb = ind.bollinger(src, n, k)
        print(vergleich(f"BB {lab} Basis %", bb["bb_basis"], df["Basis"], 100, px))
        print(vergleich(f"BB {lab} Upper %", bb["bb_upper"], df["Upper.1"], 100, px))
    nw = ind.nw_envelope(c)
    print(vergleich("NW Upper (% Preis)", nw["nw_upper"], df["Upper"], 1000, px))
    print(vergleich("NW Lower (% Preis)", nw["nw_lower"], df["Lower"], 1000, px))


if __name__ == "__main__":
    for p in sorted(REF.glob("*.csv")):
        pruefe(p)
