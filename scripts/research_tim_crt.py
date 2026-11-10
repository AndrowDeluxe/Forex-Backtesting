"""Tim (Elite Coaching, Call "OC CRT"): Candle Range Theory -- T1, T2, T3.

    python -m scripts.research_tim_crt          # IS 2016-2021 + OOS 2022-2024 (OOS frei seit 10.11.)

Vorab festgelegte Definitionen (knowledge/resources/tim-oc-crt-call.md, Abschnitt 5):
  CRT short  C2.high > C1.high, C1.low < C2.close < C1.high, C2.low >= C1.low (nur eine Seite gesweept).
  CRT long   spiegelbildlich.
  Trade      Einstieg Schluss C2, Stop = Sweep-Extrem von C2, Ziel = anderes Extrem von C1,
             max. 12 Kerzen, sonst Ausstieg zum Schluss. Stop und Ziel in derselben Kerze = Stop.
  Kosten     Round-Trip-Spread in R (Gold 0,30 $, EURUSD 1,0 Pip), wie htf_daily_trade.
  T1         alle CRTs; Kontrolle = Kerze 2 schliesst JENSEITS von C1 (Bruch), gleiche Trade-Geometrie.
  T2         "Early Ones": juengstes bestaetigtes Swing-Hoch (Fractal 2/2) der 20 Kerzen vor C1, das
             ueber C1.high liegt (long: Swing-Tief unter C1.low).
             geholt = C2 laeuft darueber; fehlt = Swing existiert, C2 bleibt darunter; kein = kein Swing.
             Tims Behauptung: "geholt" kommt seltener hinter den Sweep-Docht zurueck (Stopquote).
  T3         Break-even nach +0,5 R gegen kein BE, getrennt nach T2-Gruppe.
  Kerzen     aus M15 gebaut; H4/D1 an der Broker-Serverzeit (New York + 7 h) ausgerichtet.
  T4         (Eroeffnung jenseits des Vorschlusses) entfaellt: FX/Gold intraday praktisch ohne Gaps.

Muster-Erkennung: fusion_lab/patterns/crt.py (Baustein, seit 10.11.).
Overfitting-Sperre `tim_crt`: 4 Timeframes x (T1, T2, T3) = 12 gezaehlte Varianten.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.patterns.crt import detect, resample_server as resample
from research_lock import Lock, deflated_sharpe

LOCK = Lock("tim_crt")
MARKETS = {"XAUUSD": ("data_cache/combined/GOLD_M15_2016-01-01_2026-08-01.parquet", 0.30),
           "EURUSD": ("data_cache/combined/EURUSD_M15_2016-01-01_2026-07-29.parquet", 0.00010)}
TFS = ("M15", "H1", "H4", "D1")
MAX_HOLD, BE_AT = 12, 0.5


def load(path: str) -> pd.DataFrame:
    d = pd.read_parquet(path)[["Open", "High", "Low", "Close"]].sort_index()
    return d[~d.index.duplicated(keep="last")]


def trade(i1: int, side: str, stop: float, target: float, o, h, l, c, cost: float, be: bool) -> dict | None:
    entry = c[i1]
    risk = (stop - entry) if side == "short" else (entry - stop)
    if risk <= 0:
        return None
    sgn = -1 if side == "short" else 1
    cur_stop, last = stop, min(i1 + MAX_HOLD, len(c) - 1)
    if last <= i1:
        return None
    for k in range(i1 + 1, last + 1):
        hit_stop = h[k] >= cur_stop if side == "short" else l[k] <= cur_stop
        hit_tgt = l[k] <= target if side == "short" else h[k] >= target
        if hit_stop:
            r = sgn * (cur_stop - entry) / risk
            return {"r": r - cost / risk, "r_gross": r, "stop": cur_stop == stop, "tgt": False, "k": k}
        if hit_tgt:
            return {"r": abs(target - entry) / risk - cost / risk, "r_gross": abs(target - entry) / risk,
                    "stop": False, "tgt": True, "k": k}
        fav = (entry - l[k]) if side == "short" else (h[k] - entry)
        if be and fav >= BE_AT * risk:
            cur_stop = entry
    r = sgn * (c[last] - entry) / risk
    return {"r": r - cost / risk, "r_gross": r, "stop": False, "tgt": False, "k": last}


def scan(x: pd.DataFrame, cost: float) -> pd.DataFrame:
    o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    rows = []
    for _, sig in detect(x).iterrows():
        for be in (False, True):
            if sig["typ"] == "Bruch" and be:
                continue
            t = trade(sig["i1"], sig["side"], sig["stop"], sig["target"], o, h, l, c, cost, be)
            if t is None:
                continue
            rows.append({"t": sig["t"], "side": sig["side"], "typ": sig["typ"], "grp": sig["grp"], "be": be, **t})
    return pd.DataFrame(rows).set_index("t")


def summary(d: pd.DataFrame) -> dict:
    r = d["r"]
    n = len(r)
    if n < 2:
        return {"n": n}
    t = r.mean() / r.std(ddof=1) * np.sqrt(n)
    return {"n": n, "ziel%": 100 * d["tgt"].mean(), "stop%": 100 * d["stop"].mean(),
            "R_brutto": d["r_gross"].mean(), "R_netto": r.mean(), "t_netto": t}


def table(res: pd.DataFrame, stage) -> pd.DataFrame:
    out = {}
    for (m, tf), g in res.groupby(["markt", "tf"], sort=False):
        g = stage(g.set_index("t"))
        nob = g[~g["be"]]
        out[(m, tf, "T1 CRT")] = summary(nob[nob["typ"] == "CRT"])
        out[(m, tf, "T1 Kontrolle Bruch")] = summary(nob[nob["typ"] == "Bruch"])
        for grp in ("geholt", "fehlt", "kein"):
            out[(m, tf, f"T2 {grp}")] = summary(nob[(nob["typ"] == "CRT") & (nob["grp"] == grp)])
        crt = g[g["typ"] == "CRT"]
        for grp in ("geholt", "fehlt"):
            out[(m, tf, f"T3 {grp} BE")] = summary(crt[(crt["grp"] == grp) & crt["be"]])
    return pd.DataFrame(out).T


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    parts = []
    for m, (path, cost) in MARKETS.items():
        m15 = load(path)
        for tf in TFS:
            r = scan(resample(m15, tf), cost).reset_index()
            r["markt"], r["tf"] = m, tf
            parts.append(r)
    res = pd.concat(parts, ignore_index=True)
    n_trials = LOCK.log_trials(12, "T1/T2/T3 je M15/H1/H4/D1, Definitionen vorab im Docstring")
    pd.set_option("display.width", 200, "display.max_rows", 200)
    fmt = {"n": "{:.0f}", "ziel%": "{:.1f}", "stop%": "{:.1f}", "R_brutto": "{:+.3f}",
           "R_netto": "{:+.3f}", "t_netto": "{:+.2f}"}
    for name, stage in (("IS 2016-2021", LOCK.is_only), ("OOS 2022-2024", LOCK.oos_only)):
        tab = table(res, stage)
        print(f"\n===== {name} (Versuche gesamt {n_trials}) =====")
        print(tab.apply(lambda col: col.map(lambda v, f=fmt.get(col.name, "{}"): "" if pd.isna(v) else f.format(v))))
        tab.to_csv(f"scripts/research_tim_crt_{name[:3].strip().lower()}.csv")
    is_crt = LOCK.is_only(res.set_index("t"))
    best = is_crt[(is_crt["typ"] == "CRT") & ~is_crt["be"]]
    for (m, tf), g in best.groupby(["markt", "tf"]):
        sr = g["r"].mean() / g["r"].std(ddof=1)
        print(f"DSR IS {m} {tf} CRT: {deflated_sharpe(sr, len(g), n_trials):.2f}")


if __name__ == "__main__":
    main()
