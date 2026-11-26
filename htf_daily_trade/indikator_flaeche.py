"""Kandidat "Multi-Length-Flaeche >= 50 % + RSI-MA-Cross" (Daily) weiter ausgefuehrt (Nutzerauftrag 26.11.2026).

    python -m htf_daily_trade.indikator_flaeche

Lock `indikator_kombi_daily` (gleicher Split, Tresor zu). Parameter-Nachbarschaft auf IS:
  A Flaechen-Schwelle 30/50/70/90 | L Fenster 1/3/5 Tage | H Haltedauer 5/10/15/20 | B Stop-Puffer 0,2/0,5/1,0 ATR
  (Trigger RSI(14) kreuzt SMA(14), Einstieg Open Folgetag, Stop 5-Tage-Extrem - B x ATR).
Basis A50 L3 H10 B0.2 = Teil-A-Kandidat "Z2 G1 C0 X1". Dazu: Jahre, Seiten, Maerkte, ohne Top-5,
Swap-Naeherung (0,01 R je Haltetag), Monte-Carlo (Bootstrap 5000 x, 1 % Risiko, Reihenfolge zufaellig).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade import indikatoren as ind
from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS, load_market
from htf_daily_trade.indikator_edge import IS_END, IS_START, LOCK, OOS_END
from research_lock import Lock

AS, LS, HS, BS = (30, 50, 70, 90), (1, 3, 5), (5, 10, 15, 20), (0.2, 0.5, 1.0)
SWAP_R_TAG = 0.01


def run(name: str) -> list[dict]:
    d = load_market(name).rename(columns=str.lower).loc[:OOS_END]
    a = ind.alle(d)
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = a["atr"].to_numpy()
    start = d.index.searchsorted(pd.Timestamp(IS_START))
    out = []
    for A, L, H, B in itertools.product(AS, LS, HS, BS):
        for sg, area, cross in ((1, "rsi_ml_os_area", "rsi_cross_up"), (-1, "rsi_ml_ob_area", "rsi_cross_dn")):
            zone = (a[area] >= A).astype(float).rolling(L, min_periods=1).max().fillna(0).astype(bool).to_numpy()
            m = zone & a[cross].fillna(False).to_numpy()
            busy = -1
            for t in np.flatnonzero(m):
                if t < max(start, 5) or t + 1 >= len(o) or t <= busy or np.isnan(atr[t]):
                    continue
                e = o[t + 1]
                stop = l[t - 4:t + 1].min() - B * atr[t] if sg == 1 else h[t - 4:t + 1].max() + B * atr[t]
                risk = (e - stop) * sg
                if risk <= 0:
                    continue
                last = min(t + H, len(o) - 1)
                seg = l[t + 1:last + 1] <= stop if sg == 1 else h[t + 1:last + 1] >= stop
                if seg.any():
                    j = t + 1 + int(np.argmax(seg))
                    ex = stop
                else:
                    j, ex = last, c[last]
                busy = j
                tage = j - t
                r = ((ex - e) * sg - MARKETS[name][2]) / risk
                out.append({"variante": f"A{A} L{L} H{H} B{B}", "markt": name, "seite": "long" if sg == 1 else "short",
                            "datum": d.index[t], "r": r, "r_swap": r - SWAP_R_TAG * tage, "tage": tage})
    return out


def mc(r: np.ndarray, n: int = 5000, risk: float = 0.01, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    dds, means = [], []
    for _ in range(n):
        s = rng.choice(r, len(r), replace=True)
        eq = np.cumprod(1 + risk * s)
        dds.append((eq / np.maximum.accumulate(eq) - 1).min())
        means.append(s.mean())
    return {"mean_p5": np.percentile(means, 5), "p_mean_neg": np.mean(np.array(means) < 0),
            "dd_median": np.median(dds), "dd_p95": np.percentile(dds, 5)}


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    lock = Lock(LOCK)
    if lock.trials <= 54:
        lock.log_trials(len(AS) * len(LS) * len(HS) * len(BS), "Flaeche-Kandidat: A x L x H x B Nachbarschaft (26.11.)")
    t = pd.DataFrame([r for name in MARKETS for r in run(name)])
    t["periode"] = np.where(t["datum"] <= pd.Timestamp(IS_END), "IS", "OOS")
    t.to_parquet("htf_daily_trade/indikator_flaeche_trades.parquet")
    g = t.groupby(["variante", "periode"])["r"].agg(["count", "mean"]).unstack()
    g.columns = [f"{p}_{k}" for k, p in g.columns]
    g = g.reset_index()
    for col, i in (("A", 0), ("L", 1), ("H", 2), ("B", 3)):
        g[col] = g["variante"].str.split().str[i]
    g.to_csv("htf_daily_trade/indikator_flaeche_varianten.csv", index=False)
    print("== Nachbarschaft: Mittel je Parameterwert (IS / OOS, alle anderen Parameter gemittelt)")
    for col in ("A", "L", "H", "B"):
        print(g.groupby(col)[["IS_mean", "OOS_mean"]].mean().round(3).T.to_string(), "\n")
    print("== Anteil Varianten mit IS > 0:", round((g["IS_mean"] > 0).mean(), 2), " OOS > 0:", round((g["OOS_mean"] > 0).mean(), 2))
    print(g.sort_values("IS_mean", ascending=False).head(10).round(3).to_string(index=False))
    base = t[t["variante"] == "A50 L3 H10 B0.2"].copy()
    print("\n== Basis A50 L3 H10 B0.2")
    for p, gp in base.groupby("periode"):
        st = stats(gp["r"])
        top = gp["r"].sort_values(ascending=False)
        print(p, {k: round(v, 3) for k, v in st.items()}, "| mit Swap", round(gp["r_swap"].mean(), 3),
              "| ohne Top5", round(top.iloc[5:].mean(), 3), "| Ø Tage", round(gp["tage"].mean(), 1))
    base["jahr"] = base["datum"].dt.year
    print(base.pivot_table(index="jahr", values="r", aggfunc=["count", "mean", "sum"]).round(2).T.to_string())
    print(base.pivot_table(index="seite", columns="periode", values="r", aggfunc=["count", "mean"]).round(2).to_string())
    print("MC IS+OOS (mit Swap):", {k: round(v, 3) for k, v in mc(base["r_swap"].to_numpy()).items()})
