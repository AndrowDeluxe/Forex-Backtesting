"""Tick-Erzeugung des MT5-Testers im Modell "1 Minute OHLC".

Je M1-Kerze vier Bid-Ticks: Open (Sekunde 0), dann bei steigender Kerze
Low/High, bei fallender High/Low (Sekunde 20/40), Close (Sekunde 59).
Ask = Bid + Kerzen-Spread. Die Sekunden 0/20/40/59 decken sich mit den
Einstiegszeiten in den Valkyrie-OHLC-Berichten (z. B. 15:14:40, 20:19:59).
"""

import numpy as np
import pandas as pd

_OFFS = np.array([0, 20, 40, 59], dtype="timedelta64[s]")


def ticks(m1: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = (m1[k].to_numpy() for k in ("open", "high", "low", "close"))
    up = c >= o
    p2 = np.where(up, l, h)
    p3 = np.where(up, h, l)
    bid = np.column_stack([o, p2, p3, c]).ravel()
    t = (m1.index.to_numpy()[:, None] + _OFFS[None, :]).ravel()
    spread = np.repeat(m1["spread"].to_numpy() / 100.0, 4)
    return pd.DataFrame({"bid": bid, "ask": bid + spread}, index=pd.DatetimeIndex(t, name="t"))
