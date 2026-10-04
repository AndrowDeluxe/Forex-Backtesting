"""Faber (2013), "A Quantitative Approach to Tactical Asset Allocation" (SSRN 962461).

Phase-4-Nachbau (Backtest-Standardprozess) + Robustheits-Basischecks.

Regel (Paper S. 21-22): am letzten Handelstag des Monats je Anlageklasse
long, wenn Monatsschluss > SMA(10 Monatsschluesse), sonst 1/N-Anteil in
T-Bills. Gleichgewichtet, monatlich rebalanciert, Fill zum Monatsschluss.

Universen:
  ETF   : SPY, EFA, IEF, DBC, VNQ (ab 2006-02, handelbar)
  FONDS : VFINX, VGTSX, VUSTX, PCRIX, FRESX (ab 2002-07, laengere Proxy-Historie)
Cash: ^IRX (13-Wochen-T-Bill-Rendite) / 12.

Fenster: Paper-OOS 2006-2012 (vom Paper selbst als OOS markiert) und
ECHTES OOS 2013-03..heute (nach dem Update vom Feb. 2013).
"""
import json
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSES = {
    "ETF": ["SPY", "EFA", "IEF", "DBC", "VNQ"],
    "FONDS": ["VFINX", "VGTSX", "VUSTX", "PCRIX", "FRESX"],
}
OUT = "Claude outputs/faber_gtaa.json"


def load():
    tick = sorted({t for u in UNIVERSES.values() for t in u} | {"^IRX"})
    px = yf.download(tick, start="1995-01-01", auto_adjust=True, progress=False)["Close"]
    return px


def monthly(px):
    m = px.resample("ME").last()
    rf = (m["^IRX"] / 100 / 12).shift(1)  # Rendite des Monats t aus Satz am Ende t-1
    return m.drop(columns="^IRX"), rf


def stats(r, rf):
    r = r.dropna()
    rf = rf.reindex(r.index).fillna(0)
    n = len(r)
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (12 / n) - 1
    vol = r.std() * np.sqrt(12)
    ex = r - rf
    sharpe = ex.mean() / ex.std() * np.sqrt(12) if ex.std() > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    return {"n_m": n, "cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2),
            "sharpe": round(sharpe, 2), "maxdd": round(dd * 100, 2)}


def run(m, rf, sma=10, lag=0, cost_bps=0.0, sig_kind="sma"):
    """Gibt (timing, buyhold, invested_share, switches_pro_jahr) zurueck."""
    ret = m.pct_change()
    if sig_kind == "sma":
        sig = (m > m.rolling(sma).mean()).astype(float)
    elif sig_kind == "tsmom12":  # Kontrollgruppe: 12M-Absolute-Momentum
        sig = (m.pct_change(12) > rf.rolling(12).sum().values[:, None]).astype(float)
    elif sig_kind == "random":
        rng = np.random.default_rng(lag)
        sig = pd.DataFrame(rng.random(m.shape) < 0.71, index=m.index, columns=m.columns).astype(float)
        lag = 0
    sig = sig.where(m.rolling(sma).mean().notna())
    # lag in Monaten: Signal aus t-1-lag gilt fuer Rendite in t
    pos = sig.shift(1 + lag)
    valid = pos.notna().all(axis=1) & ret.notna().all(axis=1)
    pos, r = pos[valid], ret[valid]
    rfv = rf.reindex(r.index).fillna(0)
    w = 1 / m.shape[1]
    sw = pos.diff().abs().fillna(0)
    timing = (w * (pos * r).sum(axis=1) + w * ((1 - pos).sum(axis=1)) * rfv
              - w * sw.sum(axis=1) * cost_bps / 1e4)
    bh = r.mean(axis=1)
    return timing, bh, pos.mean().mean(), sw.sum().sum() / (len(r) / 12)


def window(s, a, b=None):
    return s.loc[a:b] if b else s.loc[a:]


def main():
    px = load()
    res = {}
    for name, tick in UNIVERSES.items():
        m, rf = monthly(px[tick + ["^IRX"]])
        t, bh, inv, swy = run(m, rf)
        r = {"investiert": round(inv * 100, 1), "wechsel_pro_jahr_gesamt": round(swy, 2)}
        for lab, a, b in [("gesamt", None, None), ("paper_oos_2006_2012", "2006-01", "2012-12"),
                          ("echtes_oos_2013_heute", "2013-03", None),
                          ("ohne_2008", None, None)]:
            if lab == "ohne_2008":
                tt, bb = t[t.index.year != 2008], bh[bh.index.year != 2008]
            else:
                tt, bb = (window(t, a, b), window(bh, a, b)) if a else (t, bh)
            r[lab] = {"timing": stats(tt, rf), "buyhold": stats(bb, rf),
                      "von": str(tt.index[0].date()), "bis": str(tt.index[-1].date())}
        # Jahresreihe (OOS)
        yr = pd.DataFrame({"timing": (1 + t).groupby(t.index.year).prod() - 1,
                           "buyhold": (1 + bh).groupby(bh.index.year).prod() - 1}).round(4) * 100
        r["jahre"] = yr.to_dict(orient="index")
        # Parameter-Plateau
        r["sma_plateau_oos2013"] = {k: stats(window(run(m, rf, sma=k)[0], "2013-03"), rf)
                                    for k in (3, 6, 8, 9, 10, 11, 12)}
        # Ausfuehrungs-Lag: 1 Monat spaeter (grob, Obergrenze fuer Verzoegerung)
        r["lag_1m_oos2013"] = stats(window(run(m, rf, lag=1)[0], "2013-03"), rf)
        # Kosten-Sensitivitaet (je Wechsel und Anteil, einseitig)
        r["kosten_oos2013"] = {f"{c}bps": stats(window(run(m, rf, cost_bps=c)[0], "2013-03"), rf)
                               for c in (0, 10, 25, 50)}
        # Kontrollgruppen
        r["kontrolle_tsmom12_oos2013"] = stats(window(run(m, rf, sig_kind="tsmom12")[0], "2013-03"), rf)
        rnd = [stats(window(run(m, rf, sig_kind="random", lag=s)[0], "2013-03"), rf) for s in range(200)]
        tim_oos = stats(window(t, "2013-03"), rf)
        r["kontrolle_zufall71pct_oos2013"] = {
            "sharpe_median": float(np.median([x["sharpe"] for x in rnd])),
            "maxdd_median": float(np.median([x["maxdd"] for x in rnd])),
            "anteil_zufall_sharpe_ge_timing": float(np.mean([x["sharpe"] >= tim_oos["sharpe"] for x in rnd])),
            "anteil_zufall_maxdd_besser_timing": float(np.mean([x["maxdd"] >= tim_oos["maxdd"] for x in rnd])),
        }
        # Mechanismus-Check (Paper Fig. 18): Rendite/Vola im Folgemonat ober- vs. unterhalb SMA, je Asset
        ret = m.pct_change()
        above = (m > m.rolling(10).mean()).shift(1)
        mech = {}
        for a in m.columns:
            for lab, a0 in [("gesamt", None), ("oos2013", "2013-03")]:
                x = ret[a] if a0 is None else ret[a].loc[a0:]
                ab = above[a].reindex(x.index)
                up, dn = x[ab == True], x[ab == False]  # noqa: E712
                mech.setdefault(a, {})[lab] = {
                    "anteil_ueber": round(len(up) / (len(up) + len(dn)) * 100, 1),
                    "ret_ueber_pa": round(up.mean() * 1200, 2), "ret_unter_pa": round(dn.mean() * 1200, 2),
                    "vol_ueber": round(up.std() * np.sqrt(12) * 100, 2), "vol_unter": round(dn.std() * np.sqrt(12) * 100, 2),
                    "n_unter": int(len(dn))}
        r["mechanismus_fig18"] = mech
        # Block-Bootstrap: Sharpe-Differenz Timing - B&H im OOS (12-Monats-Bloecke)
        d = pd.DataFrame({"t": window(t, "2013-03"), "b": window(bh, "2013-03")}).dropna()
        rng = np.random.default_rng(0)
        L, n = 12, len(d)
        diffs = []
        for _ in range(2000):
            idx = np.concatenate([np.arange(s, s + L) % n for s in rng.integers(0, n, n // L + 1)])[:n]
            s_ = d.iloc[idx]
            sh = lambda x: x.mean() / x.std() * np.sqrt(12)
            diffs.append(sh(s_["t"]) - sh(s_["b"]))
        r["bootstrap_sharpe_diff_oos2013"] = {"p05": round(float(np.percentile(diffs, 5)), 2),
                                              "median": round(float(np.median(diffs)), 2),
                                              "p95": round(float(np.percentile(diffs, 95)), 2),
                                              "anteil_le_0": round(float(np.mean(np.array(diffs) <= 0)), 3)}
        res[name] = r
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for name, r in res.items():
        print("=" * 20, name, "investiert", r["investiert"], "% | Wechsel/J", r["wechsel_pro_jahr_gesamt"])
        for k in ("gesamt", "paper_oos_2006_2012", "echtes_oos_2013_heute", "ohne_2008"):
            print(k, r[k]["von"], r[k]["bis"], "\n  T", r[k]["timing"], "\n  B", r[k]["buyhold"])
        print("plateau", {k: (v["sharpe"], v["maxdd"], v["cagr"]) for k, v in r["sma_plateau_oos2013"].items()})
        print("lag1m", r["lag_1m_oos2013"])
        print("kosten", {k: v["cagr"] for k, v in r["kosten_oos2013"].items()})
        print("tsmom12", r["kontrolle_tsmom12_oos2013"])
        print("zufall", r["kontrolle_zufall71pct_oos2013"])
        print("bootstrap", r["bootstrap_sharpe_diff_oos2013"])
        for a, v in r["mechanismus_fig18"].items():
            print(" mech", a, v)
        print(" jahre", {y: (v["timing"], v["buyhold"]) for y, v in r["jahre"].items() if y >= 2007})


if __name__ == "__main__":
    main()
