"""H1-Pruefung des Fib-Limit-Kandidaten (Nutzerauftrag 26.11.2026).

    python -m htf_daily_trade.indikator_fib_h1

Gleiche Regeln wie indikator_fib_limit (A80, Stoch- oder RSI-Cross, Limit 0,5-Fib, Stop Signal-Extrem + 0,25 ATR,
10 Tage), aber Fuellung, Stop und Ausstieg Kerze fuer Kerze auf H1 (h4_manip.intraday). Tageskerzen aus denselben
H1-Daten, zwei Tagesdefinitionen:
  UTC     Tageswechsel 00:00 UTC (wie die Dukascopy-D1-Dateien des Backtests)
  SERVER  Broker-Tag New York 17:00 (= TradingView FXCM/OANDA-Daily, Serverzeit NY+7)
In der Fuellkerze zaehlt ein Stop-Treffer als Verlust (konservativ). Gilt fuer V1 und V3, S2 und S3.
Kein neuer Parameter -> keine neuen Trials im Lock `indikator_fib_limit` (nur Ausfuehrungspruefung).

Robustheit Tagesgrenze (27.11.): `--tagesgrenzen` rechnet zusaetzlich NY0 (Mitternacht New York), UTC22
(22:00 UTC = FX-Wochenstart), FFM0 (Mitternacht Frankfurt), LDN7 (07:00 London). Traegt der Edge nur auf einer
Grenze, ist er Zufall der Kerzeneinteilung.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from htf_daily_trade import h4_manip as hm
from htf_daily_trade import indikatoren as ind
from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS
from htf_daily_trade.indikator_fib_limit import IS_END, IS_START, OOS_END

A, F, HOLD = 80, 0.5, 10
VARS = [(1, 0.25), (3, 0.25), (3, 0.5)]
# Tagesgrenze: (Zeitzone, Verschiebung in h) -> Tag = Datum von (Ortszeit + Verschiebung)
MODES = {"SERVER": ("America/New_York", 7), "NY0": ("America/New_York", 0), "UTC22": ("UTC", 2),
         "FFM0": ("Europe/Berlin", 0), "LDN7": ("Europe/London", -7)}


def days_from_h1(b: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Tageskerzen + Tagesnummer je H1-Kerze."""
    if mode == "UTC":
        key = b.index.tz_convert("UTC").tz_localize(None).normalize()
    else:
        tz, shift = MODES[mode]
        key = (b.index.tz_convert(tz).tz_localize(None) + pd.Timedelta(hours=shift)).normalize()
        key = key.where(key.dayofweek != 6, key + pd.Timedelta(days=1)).where(key.dayofweek != 5, key - pd.Timedelta(days=1))
    key = pd.DatetimeIndex(key)
    g = b.groupby(key)
    d = pd.DataFrame({"open": g["Open"].first(), "high": g["High"].max(), "low": g["Low"].min(), "close": g["Close"].last()})
    d = d[d.index.dayofweek < 5]
    day_no = d.index.get_indexer(key)
    return d, day_no


def run(name: str, mode: str) -> list[dict]:
    b = hm.intraday(name)
    b = b[(b.index >= pd.Timestamp("2014-01-01", tz="UTC")) & (b.index <= pd.Timestamp(OOS_END, tz="UTC") + pd.Timedelta(days=20))]
    d, day_no = days_from_h1(b, mode)
    a = ind.alle(d)
    o1, h1, l1, c1 = (b[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    first_bar = pd.Series(np.arange(len(b))).groupby(day_no).min()
    last_bar = pd.Series(np.arange(len(b))).groupby(day_no).max()
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    atr = a["atr"].to_numpy()
    w3 = lambda x: x.astype(float).rolling(3, min_periods=1).max().fillna(0).astype(bool).to_numpy()
    n = len(d)
    start, stop_i = d.index.searchsorted(pd.Timestamp(IS_START)), d.index.searchsorted(pd.Timestamp(OOS_END))
    out = []
    for V, buf in VARS:
        for sg in (1, -1):
            zone = w3(a["rsi_ml_os_area"] >= A) if sg == 1 else w3(a["rsi_ml_ob_area"] >= A)
            cr = (a["stoch_cross_up"] | a["rsi_cross_up"]) if sg == 1 else (a["stoch_cross_dn"] | a["rsi_cross_dn"])
            busy = -1
            for t in np.flatnonzero(zone & cr.fillna(False).to_numpy()):
                if t < start or t >= stop_i or t + HOLD + V >= n or t <= busy or np.isnan(atr[t]) or t + 1 not in first_bar.index:
                    continue
                rng = h[t] - l[t]
                if rng <= 0:
                    continue
                lim = h[t] - F * rng if sg == 1 else l[t] + F * rng
                stop = l[t] - buf * atr[t] if sg == 1 else h[t] + buf * atr[t]
                i0 = first_bar[t + 1]
                i1 = last_bar.get(t + V, last_bar.iloc[-1])
                fill, e = None, None
                for i in range(i0, i1 + 1):
                    if (o1[i] <= lim) if sg == 1 else (o1[i] >= lim):
                        fill, e = i, o1[i]
                    elif (l1[i] <= lim) if sg == 1 else (h1[i] >= lim):
                        fill, e = i, lim
                    if fill is not None:
                        break
                if fill is None:
                    busy = t + V
                    continue
                risk = (e - stop) * sg
                if risk <= 0:
                    busy = day_no[fill]
                    continue
                end_day = min(day_no[fill] + HOLD, n - 1)
                i_end = last_bar.get(end_day, len(b) - 1)
                seg = l1[fill:i_end + 1] <= stop if sg == 1 else h1[fill:i_end + 1] >= stop
                if seg.any():
                    j = fill + int(np.argmax(seg))
                    ex = min(stop, o1[j]) if sg == 1 and j > fill else (max(stop, o1[j]) if sg == -1 and j > fill else stop)
                else:
                    j, ex = i_end, c1[i_end]
                busy = day_no[j]
                r = ((ex - e) * sg - MARKETS[name][2]) / risk
                out.append({"modus": mode, "variante": f"V{V} S+{buf}", "markt": name,
                            "seite": "long" if sg == 1 else "short", "signal": d.index[t], "r": r,
                            "fuell_tag_stop": bool(seg.any() and day_no[j] == day_no[fill]),
                            "luecke_stop": bool(seg.any() and j > fill and ((o1[j] < stop) if sg == 1 else (o1[j] > stop)))})
    return out


if __name__ == "__main__":
    import sys
    pd.set_option("display.width", 200)
    alle = "--tagesgrenzen" in sys.argv
    modes = ["UTC", *MODES] if alle else ["UTC", "SERVER"]
    t = pd.DataFrame([r for mode in modes for name in MARKETS for r in run(name, mode)])
    t["periode"] = np.where(t["signal"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t.to_parquet("htf_daily_trade/indikator_fib_h1_trades.parquet" if not alle else "htf_daily_trade/indikator_fib_tagesgrenzen_trades.parquet")
    rows = []
    for (m, v, p), g in t.groupby(["modus", "variante", "periode"]):
        st = stats(g["r"])
        top = g["r"].sort_values(ascending=False)
        rows.append({"modus": m, "variante": v, "periode": p, "n": st["n"], "R": st["mean_r"], "t": st["t"],
                     "ohne_top3": top.iloc[3:].mean(), "fuelltag_stop": g["fuell_tag_stop"].mean(),
                     "luecke_stop": g["luecke_stop"].mean()})
    res = pd.DataFrame(rows)
    res.to_csv("htf_daily_trade/indikator_fib_tagesgrenzen.csv" if alle else "htf_daily_trade/indikator_fib_h1.csv",
               index=False)
    print(res.round(3).to_string(index=False))
    for m in modes:
        g = t[(t["modus"] == m) & (t["variante"] == "V3 S+0.25")].copy()
        g["jahr"] = g["signal"].dt.year
        print(m, g.groupby("jahr")["r"].mean().round(2).to_dict())
        print(m, g.groupby("markt")["r"].mean().round(2).to_dict())
