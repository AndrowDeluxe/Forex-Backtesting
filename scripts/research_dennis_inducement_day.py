"""Dennis' „Daily Inducement Day“ -- Test mit Dukascopy-Tick-Volumen (Plan 24.11.2026).

    python -m scripts.research_dennis_inducement_day            # Events bauen (Cache) + IS/OOS-Auswertung

Detektor und Definitionen: fusion_lab/patterns/inducement_day.py, Profile: fusion_lab/patterns/volume_profile.py.
Maerkte GBPUSD/EURUSD (M5 2016-10/2026), Gold (M1 2018-10/2026 -> M5). Kosten Round Trip in R.
Ziele: a = Tief(T-1), b = POC(T-2), c = Stop + 1,6 x (Tief(T-1) - Stop) (Long gespiegelt).
Haltedauer bis Ende des naechsten CME-Tags.
Stufe 1: POI = VA(T-2), Einstieg HTF/LTF x Ziel a/b/c = 6 Varianten; Kontrolle = dieselben Ausloeser ohne
         Trend/Inducement/POI (nackte Intraday-CRT am Vortageshoch).
Stufe 2: POI = FVG bzw. Order Block statt VA, je 6 Varianten.
Stufe 3: IS-beste Kombination + Fib-Grenze bzw. + Volumen-Divergenz/Delta-Kipp, 2 Varianten.
Sperre `dennis_inducement_day`: IS 2016-2021, OOS 2022-04/2026, Tresor 05-10/2026 (zu).
"""

from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.patterns.inducement_day import prepare, scan, simulate
from research_lock import Lock, deflated_sharpe

LOCK = Lock("dennis_inducement_day")
CACHE = Path("data_cache/smh/inducement_events.parquet")
MARKETS = {"GBPUSD": (0.0001, 0.00014), "EURUSD": (0.0001, 0.00010), "XAUUSD": (0.50, 0.30)}
TARGETS = ("a_tief_T1", "b_poc_T2", "c_exp_1.6")
OUT = "scripts/research_dennis_inducement_day"


def load(m: str) -> pd.DataFrame:
    if m != "XAUUSD":
        d = pd.read_parquet(f"data_cache/combined/{m}_M5_2016-01-01_2026-10-28.parquet")
    else:
        files = sorted(glob.glob("data_cache/combined/GOLD_M1_20*.parquet"))
        d = pd.concat([pd.read_parquet(f) for f in files]).sort_index()
        d = d[~d.index.duplicated(keep="last")]
        d = d.resample("5min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last",
                                    "Volume": "sum"}).dropna()
    d = d[["Open", "High", "Low", "Close", "Volume"]].sort_index()
    return d[~d.index.duplicated(keep="last")]


def target(ev: pd.Series, kind: str) -> float:
    if kind == "a_tief_T1":
        return ev["L1"]
    if kind == "b_poc_T2":
        return ev["poc2"]
    return ev["stop"] + 1.6 * (ev["L1"] - ev["stop"])


def build() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    rows = []
    for m, (step, cost) in MARKETS.items():
        bars = load(m)
        ctx = prepare(bars)
        ev = pd.concat([scan(bars, step, s) for s in ("short", "long")], ignore_index=True)
        for _, e in ev.iterrows():
            for k in TARGETS:
                r = simulate(ctx, e, target(e, k), cost)
                if r is not None:
                    rows.append({**e.to_dict(), "markt": m, "ziel": k, **r})
        print(f"{m}: {len(ev)} Ausloeser")
    out = pd.DataFrame(rows)
    out["t"] = pd.to_datetime(out["t"], utc=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE)
    return out


def stats(r: pd.Series) -> dict:
    n = len(r)
    if n < 3:
        return {"n": n}
    sd = r.std(ddof=1)
    return {"n": n, "treffer%": 100 * (r > 0).mean(), "R": r.mean(), "t": r.mean() / sd * np.sqrt(n) if sd else np.nan}


def table(x: pd.DataFrame, poi: str, extra: list[str] | None = None) -> pd.DataFrame:
    out = {}
    for (e, k), g in x.groupby(["einstieg", "ziel"]):
        sel = g["trend"] & g["inducement"] & g[poi]
        for f in extra or []:
            sel &= g[f]
        dennis, ctrl = g[sel], g
        s = stats(dennis["r"])
        out[(e, k)] = {**{f"{a}": b for a, b in s.items()}, "R_brutto": dennis["r_gross"].mean(),
                       "Kontrolle_n": len(ctrl), "Kontrolle_R": ctrl["r"].mean(),
                       "Kontrolle_R_brutto": ctrl["r_gross"].mean(),
                       **{f"R_{m}": dennis.loc[dennis["markt"] == m, "r"].mean() for m in MARKETS}}
    return pd.DataFrame(out).T


def matched(x: pd.DataFrame, poi: str) -> pd.DataFrame:
    """Dennis-Trades gegen Kontrolle in gleichen Stopweiten- und CRV-Klassen (CRT-Lehre 10.11.)."""
    y = x.copy()
    y["rel_risk"] = y["risk"] / (y["H1"] - y["L1"]).abs()
    y["crv"] = (y.apply(lambda e: abs(target(e, e["ziel"]) - e["entry"]), axis=1)) / y["risk"]
    out = {}
    for (e, k), g in y.groupby(["einstieg", "ziel"]):
        g = g.copy()
        g["rb"] = pd.qcut(g["rel_risk"], 4, labels=False, duplicates="drop")
        g["qb"] = pd.qcut(g["crv"], 4, labels=False, duplicates="drop")
        g["dennis"] = g["trend"] & g["inducement"] & g[poi]
        cell = g.groupby(["rb", "qb", "dennis"])["r_gross"].agg(["mean", "size"]).unstack("dennis").dropna()
        if cell.empty or True not in cell["size"].columns:
            continue
        w = cell[("size", True)]
        out[(e, k)] = {"n_dennis": int(w.sum()), "R_brutto_dennis": np.average(cell[("mean", True)], weights=w),
                       "R_brutto_kontrolle_gleiche_klasse": np.average(cell[("mean", False)], weights=w)}
    return pd.DataFrame(out).T


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2026-04-30", "2026-10-31")
    res = build().set_index("t").sort_index()
    pd.set_option("display.width", 250, "display.max_columns", 30)
    n = LOCK.log_trials(18, "Stufe 1+2: Einstieg HTF/LTF x Ziel a/b/c x POI VA/FVG/OB")
    is_, oos = LOCK.is_only(res), LOCK.oos_only(res)
    for poi in ("poi_va", "poi_fvg", "poi_ob"):
        for name, x in (("IS", is_), ("OOS", oos)):
            tab = table(x, poi)
            print(f"\n===== {poi} {name} (Versuche {n}) =====\n{tab.round(3).to_string()}")
            tab.to_csv(f"{OUT}_{poi}_{name.lower()}.csv")
    print(f"\n===== Gleiche Stopweite/CRV, IS, poi_va =====\n{matched(is_, 'poi_va').round(3).to_string()}")
    # Stufe 3 auf der IS-besten Kombination (hoechstes Ø R netto mit n >= 30)
    best = None
    for poi in ("poi_va", "poi_fvg", "poi_ob"):
        tab = table(is_, poi)
        tab = tab[tab["n"] >= 30]
        if len(tab):
            i = tab["R"].astype(float).idxmax()
            if best is None or tab.loc[i, "R"] > best[2]:
                best = (poi, i, tab.loc[i, "R"])
    if best is None:
        print("\nStufe 3 entfaellt (keine Kombination mit n >= 30)")
        return
    poi, (e, k), _ = best
    n = LOCK.log_trials(2, f"Stufe 3 auf {poi} {e} {k}: +fib, +vol_div&delta")
    print(f"\n===== Stufe 3 auf IS-Bester: {poi} {e} {k} (Versuche {n}) =====")
    for name, x in (("IS", is_), ("OOS", oos)):
        g = x[(x["einstieg"] == e) & (x["ziel"] == k)]
        for label, extra in (("Basis", []), ("+Fib 1,272-Grenze", ["fib_ok"]),
                             ("+Vol-Divergenz & Delta-Kipp", ["vol_div", "delta_kipp"])):
            sel = g["trend"] & g["inducement"] & g[poi]
            for f in extra:
                sel &= g[f]
            s = stats(g[sel]["r"])
            dsr = deflated_sharpe(s["R"] / g[sel]["r"].std(ddof=1), s["n"], n) if s["n"] >= 3 else np.nan
            print(f"{name} {label:30s} " + ", ".join(f"{a} {b:.3f}" if isinstance(b, float) else f"{a} {b}"
                                                     for a, b in s.items()) + f", DSR {dsr:.2f}")


if __name__ == "__main__":
    main()
