"""MetaTrader-Standard-ZigZag (Examples\\ZigZag.mq5) in Python.

Parameter wie im MT5-Original: Depth, Deviation (in Punkten), Backstep.
`zigzag(high, low, depth, deviation, backstep, point)` liefert zwei Arrays mit
den bestaetigten Hoch- bzw. Tiefpunkten (0 = kein Punkt), berechnet nur aus den
uebergebenen Kerzen -- fuer einen kausalen Wert zum Zeitpunkt t also nur die
Kerzen bis t-1 uebergeben.
"""

import numpy as np


def zigzag(high: np.ndarray, low: np.ndarray, depth: int = 12, deviation: int = 5,
           backstep: int = 3, point: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    n = len(high)
    hmap, lmap = np.zeros(n), np.zeros(n)
    last_low = last_high = 0.0
    dev = deviation * point
    for i in range(depth - 1, n):
        # Tief
        val = low[i - depth + 1:i + 1].min()
        if val == last_low:
            val = 0.0
        else:
            last_low = val
            if low[i] - val > dev:
                val = 0.0
            else:
                for back in range(1, backstep + 1):
                    if i - back >= 0 and lmap[i - back] != 0 and lmap[i - back] > val:
                        lmap[i - back] = 0.0
        lmap[i] = val if low[i] == val else 0.0
        # Hoch
        val = high[i - depth + 1:i + 1].max()
        if val == last_high:
            val = 0.0
        else:
            last_high = val
            if val - high[i] > dev:
                val = 0.0
            else:
                for back in range(1, backstep + 1):
                    if i - back >= 0 and hmap[i - back] != 0 and hmap[i - back] < val:
                        hmap[i - back] = 0.0
        hmap[i] = val if high[i] == val else 0.0

    # Endauswahl: abwechselnd Hoch/Tief, jeweils das extremere behalten
    zz_h, zz_l = np.zeros(n), np.zeros(n)
    whatlookfor = 0           # 0 = beides, 1 = naechstes Hoch, -1 = naechstes Tief
    last_h_pos = last_l_pos = -1
    last_h = last_l = 0.0
    for i in range(depth - 1, n):
        if whatlookfor == 0:
            if lmap[i] != 0:
                last_l, last_l_pos, whatlookfor = lmap[i], i, 1
                zz_l[i] = last_l
            elif hmap[i] != 0:
                last_h, last_h_pos, whatlookfor = hmap[i], i, -1
                zz_h[i] = last_h
        elif whatlookfor == 1:          # suche Hoch, Tief kann tiefer werden
            if lmap[i] != 0 and lmap[i] < last_l and hmap[i] == 0:
                zz_l[last_l_pos] = 0.0
                last_l, last_l_pos = lmap[i], i
                zz_l[i] = last_l
            if hmap[i] != 0 and lmap[i] == 0:
                last_h, last_h_pos, whatlookfor = hmap[i], i, -1
                zz_h[i] = last_h
        else:                            # suche Tief, Hoch kann hoeher werden
            if hmap[i] != 0 and hmap[i] > last_h and lmap[i] == 0:
                zz_h[last_h_pos] = 0.0
                last_h, last_h_pos = hmap[i], i
                zz_h[i] = last_h
            if lmap[i] != 0 and hmap[i] == 0:
                last_l, last_l_pos, whatlookfor = lmap[i], i, 1
                zz_l[i] = last_l
    return zz_h, zz_l
