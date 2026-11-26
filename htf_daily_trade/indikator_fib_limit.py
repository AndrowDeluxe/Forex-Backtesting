"""Nutzer-Idee 26.11.2026: Daily-Ausbruch (ML-Flaeche + Cross), Einstieg Limit am Fib des Signaltags.

    python -m htf_daily_trade.indikator_fib_limit

Beispiel des Nutzers: Gold 29.01.2026 extreme ML-Flaeche + Stoch-RSI-Cross, Einstieg 30.01. am Fib der
Vortagesrange -> ~4 R.
Lock `indikator_fib_limit` (IS 2016-21, OOS bis 25.05.2026, Tresor zu). 9 Maerkte Daily.
Signal (Tag t, Short gespiegelt; Short = nach OB-Flaeche):
  Flaeche  A50 / A80: OS- bzw. OB-Flaeche >= x % in den letzten 3 Tagen (inkl. t)
  Cross    GS Stoch-RSI K/D | GR RSI-MA | GX eins von beiden -- am Tag t
Einstieg  Limit long = Hoch - f x Range(t), short = Tief + f x Range(t); f = 0,5 / 0,618.
          Gueltig V1 = Tag t+1 | V3 = t+1..t+3. Oeffnet der Markt jenseits des Limits -> Fuellung zum Open.
Stop      S1 Tief(t) bzw. Hoch(t) | S2 +/- 0,25 Daily-ATR | S3 +/- 0,5 ATR
Ziel      R2 / R3 / R4 | T10 Zeitausstieg 10 Tage (alle Ziele spaetestens nach 10 Tagen zum Schluss)
Daily-Simulation: in der Fuellkerze nur der Stop (konservativ), danach Stop vor Ziel in derselben Kerze.
Kosten filter_matrix.MARKETS, Swap-Naeherung 0,01 R je Haltetag separat. Je Markt und Seite ein Trade.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade import indikatoren as ind
from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS, load_market
from research_lock import Lock, deflated_sharpe

LOCK = "indikator_fib_limit"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2026-05-25", "2026-11-25"
AS, GS, FS, VS, SS, TS = (50, 80), ("GS", "GR", "GX"), (0.5, 0.618), (1, 3), ("S1", "S2", "S3"), ("R2", "R3", "R4", "T10")
S_ATR = {"S1": 0.0, "S2": 0.25, "S3": 0.5}
SWAP_R_TAG = 0.01


def run(name: str, end: str = OOS_END) -> list[dict]:
    d = load_market(name).rename(columns=str.lower).loc[:end]
    a = ind.alle(d)
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = a["atr"].to_numpy()
    n = len(o)
    start = d.index.searchsorted(pd.Timestamp(IS_START))
    w3 = lambda b: b.astype(float).rolling(3, min_periods=1).max().fillna(0).astype(bool).to_numpy()
    out = []
    for A, G, f, V, S, T in itertools.product(AS, GS, FS, VS, SS, TS):
        for sg in (1, -1):
            zone = w3(a["rsi_ml_os_area"] >= A) if sg == 1 else w3(a["rsi_ml_ob_area"] >= A)
            sx = a["stoch_cross_up" if sg == 1 else "stoch_cross_dn"].fillna(False).to_numpy()
            rx = a["rsi_cross_up" if sg == 1 else "rsi_cross_dn"].fillna(False).to_numpy()
            cross = {"GS": sx, "GR": rx, "GX": sx | rx}[G]
            busy = -1
            for t in np.flatnonzero(zone & cross):
                if t < start or t + 1 >= n or t <= busy or np.isnan(atr[t]):
                    continue
                rng = h[t] - l[t]
                if rng <= 0:
                    continue
                lim = h[t] - f * rng if sg == 1 else l[t] + f * rng
                stop = l[t] - S_ATR[S] * atr[t] if sg == 1 else h[t] + S_ATR[S] * atr[t]
                fill_k, e = None, None
                for k in range(t + 1, min(t + 1 + V, n)):
                    if sg == 1 and o[k] <= lim:
                        fill_k, e = k, o[k]
                    elif sg == -1 and o[k] >= lim:
                        fill_k, e = k, o[k]
                    elif (l[k] <= lim) if sg == 1 else (h[k] >= lim):
                        fill_k, e = k, lim
                    if fill_k is not None:
                        break
                if fill_k is None:
                    busy = min(t + V, n - 1)
                    continue
                risk = (e - stop) * sg
                if risk <= 0:      # Open schon jenseits des Stops
                    busy = fill_k
                    continue
                last = min(fill_k + 10, n - 1)
                tgt = None if T == "T10" else e + sg * int(T[1]) * risk
                ex, j = None, last
                for k in range(fill_k, last + 1):
                    if (l[k] <= stop) if sg == 1 else (h[k] >= stop):
                        ex, j = stop, k
                        break
                    if k > fill_k and tgt is not None and ((h[k] >= tgt) if sg == 1 else (l[k] <= tgt)):
                        ex, j = tgt, k
                        break
                if ex is None:
                    ex = c[last]
                busy = j
                r = ((ex - e) * sg - MARKETS[name][2]) / risk
                out.append({"variante": f"A{A} {G} F{f} V{V} {S} {T}", "markt": name,
                            "seite": "long" if sg == 1 else "short", "signal": d.index[t], "fill": d.index[fill_k],
                            "exit": d.index[j], "einstieg": e, "stop": stop, "r": r, "r_swap": r - SWAP_R_TAG * (j - fill_k),
                            "tage": j - fill_k})
    return out


def main() -> None:
    pd.set_option("display.width", 220)
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    nv = len(AS) * len(GS) * len(FS) * len(VS) * len(SS) * len(TS)
    if lock.trials == 0:
        lock.log_trials(nv, "Fib-Limit nach ML-Flaeche + Cross: A x G x F x V x S x T (26.11.)")
    t = pd.DataFrame([r for name in MARKETS for r in run(name)])
    t["periode"] = np.where(t["signal"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t.to_parquet("htf_daily_trade/indikator_fib_limit_trades.parquet")
    rows = []
    for v, g in t.groupby("variante"):
        row = {"variante": v}
        for per in ("IS", "OOS"):
            p = g[g["periode"] == per]
            st = stats(p["r"])
            top = p["r"].sort_values(ascending=False)
            row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                        f"{per}_swap": p["r_swap"].mean(), f"{per}_ohne_top3": top.iloc[3:].mean()})
        i = g.loc[g["periode"] == "IS", "r"]
        row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), lock.trials) if len(i) > 2 else np.nan
        isg = g[g["periode"] == "IS"]
        row["maerkte+_IS"] = f"{(isg.groupby('markt')['r'].mean() > 0).sum()}/{isg['markt'].nunique()}"
        rows.append(row)
    res = pd.DataFrame(rows)
    for i, col in enumerate(("A", "G", "F", "V", "S", "T")):
        res[col] = res["variante"].str.split().str[i]
    res.to_csv("htf_daily_trade/indikator_fib_limit_varianten.csv", index=False)
    print("== Plateau: Mittel je Parameterwert")
    for col in ("A", "G", "F", "V", "S", "T"):
        print(res.groupby(col)[["IS_R", "OOS_R", "IS_swap", "OOS_swap"]].mean().round(3).T.to_string(), "\n")
    print("Anteil IS > 0:", round((res["IS_R"] > 0).mean(), 2), "| OOS > 0:", round((res["OOS_R"] > 0).mean(), 2),
          "| beide mit Swap > 0:", round(((res["IS_swap"] > 0) & (res["OOS_swap"] > 0)).mean(), 2))
    print(res.sort_values("IS_R", ascending=False).head(15).drop(columns=list("AGFVST")).round(3).to_string(index=False))
    ex = t[(t["markt"] == "XAUUSD") & (t["signal"] >= "2026-01-20") & (t["signal"] <= "2026-02-10")]
    print("\n== Nutzer-Beispiel Gold Ende Jan. 2026 (A50 GX F0.5 V1 S1 R4 und F0.618):")
    print(ex[ex["variante"].isin(["A50 GX F0.5 V1 S1 R4", "A50 GX F0.618 V1 S1 R4", "A50 GS F0.5 V1 S1 T10"])]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main()
