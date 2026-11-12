"""Makro als Filter ueber tragende Edges (Makro-Agent v3, Phase 5, 12.11.2026).

    python -m scripts.research_macro_filter --stage is|oos

Frage: Verbessern Makro-Zustand, Realzins-Trend oder Scorecard die Trades von Edges, die schon tragen?
Edges (Trade-Listen aus dem Repo, R netto):
- Gold ASB: asian_range_breakout/results/paper_filters_blind_trades.csv (2010-15, Basis) +
  is_reopt_trades_cost.csv (2016-11 bis 2026-09)
- Daily C2: htf_daily_trade/c2_blind_trades.csv (2010-15) + c2_kandidat_trades.csv (2016-24), R = r_TTP
- NY-Open ORB: ny_open_orb/results/is_only_7p_trades_oos.csv (2016-07 bis 2025-09; im Tresor durchgefallen,
  nur zum Vergleich)

Varianten VORAB festgelegt (Lock `macro_filter_v1`, je Edge hoechstens 3, gezaehlt):
- V1 Stress (alle Edges): kein Trade, wenn am Vortag TAIL (2 von VIX > 28, HY > 3,5, Brent > 120, OAT-Bund > 180)
  oder STLFSI > 1 (scripts.research_macro_scorecard.regime_halves).
- V2 Realzins (Gold-Trades von ASB und C2): long gesperrt, wenn der US-Realzins 10J ueber 20 Handelstage bis
  zum Vortag gestiegen ist; short gesperrt, wenn er gefallen ist.
- V3 Scorecard (FX-Trades von C2): gesperrt, wenn die Score-Differenz des Paares am Vortag mit >= 0,75 gegen
  die Trade-Richtung steht.
Kennzahlen je Stufe: n, Ø R, Σ R, MaxDD (R), t; dazu Ø R der herausgefilterten Trades. Tresor bleibt zu.
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import factors, geo_framework, panels
from research_lock import Lock

LOCK = Lock("macro_filter_v1")
SPLIT = ("2010-01-01", "2018-12-31", "2026-05-10", "2026-11-10")
SCORE_CUT = 0.75
OUT = geo_framework.ROOT / "fusion_lab" / "data" / "macro_agent" / "macro_filter_test.json"
VARIANTS = {"asb": ["V1", "V2"], "c2": ["V1", "V2", "V3"], "orb": ["V1"]}


def _day(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s.astype(str).str[:10])
    return t


def load_trades() -> dict[str, pd.DataFrame]:
    root = geo_framework.ROOT
    a1 = pd.read_csv(root / "asian_range_breakout/results/paper_filters_blind_trades.csv")
    a1 = a1[a1["variante"] == "Basis"]
    a2 = pd.read_csv(root / "asian_range_breakout/results/is_reopt_trades_cost.csv")
    asb = pd.concat([pd.DataFrame({"tag": _day(a1["time"]), "markt": "XAUUSD", "seite": np.nan, "r": a1["r"]}),
                     pd.DataFrame({"tag": _day(a2["time"]), "markt": "XAUUSD",
                                   "seite": np.where(a2["dir"] > 0, "long", "short"), "r": a2["r"]})])
    c1 = pd.read_csv(root / "htf_daily_trade/c2_blind_trades.csv")
    c2 = pd.read_csv(root / "htf_daily_trade/c2_kandidat_trades.csv")
    c2df = pd.concat([pd.DataFrame({"tag": _day(c["einstieg"]), "markt": c["markt"], "seite": c["seite"], "r": c["r_TTP"]})
                      for c in (c1, c2)])
    o = pd.read_csv(root / "ny_open_orb/results/is_only_7p_trades_oos.csv")
    orb = pd.DataFrame({"tag": _day(o["time"]), "markt": o["instrument"], "seite": np.nan, "r": o["r"]})
    return {k: v.sort_values("tag").reset_index(drop=True) for k, v in (("asb", asb), ("c2", c2df), ("orb", orb))}


def stress_days(days: pd.DatetimeIndex) -> pd.Series:
    from scripts.research_macro_scorecard import regime_halves
    return regime_halves(days) < 1.0  # bereits auf den Vortag verschoben


def realzins_trend(days: pd.DatetimeIndex) -> pd.Series:
    rz = geo_framework.history()["real_10y"].dropna()
    chg = rz.diff(20).shift(1)  # bis zum Vortag
    return chg.reindex(chg.index.union(days)).ffill().reindex(days)


def score_diff(trades: pd.DataFrame) -> pd.Series:
    p = panels.build(pd.Timestamp(SPLIT[3]), point_in_time=False)
    days = pd.bdate_range("2009-01-02", SPLIT[3])
    sc = factors.scorecard(p, days)["score"].shift(1)  # Wert des Vortags
    out = []
    for _, t in trades.iterrows():
        m = t["markt"]
        base, quote = panels.CCY_LAND.get(m[:3]), panels.CCY_LAND.get(m[3:6])
        if base is None or quote is None or t["tag"] not in sc.index:
            out.append(np.nan)
            continue
        row = sc.loc[t["tag"]]
        out.append(row.get(base, np.nan) - row.get(quote, np.nan))
    return pd.Series(out, index=trades.index)


def masks(edge: str, t: pd.DataFrame, stress: pd.Series, rz: pd.Series, sd: pd.Series | None) -> dict[str, pd.Series]:
    keep = {}
    keep["V1"] = ~t["tag"].map(stress).fillna(False).astype(bool)
    if "V2" in VARIANTS[edge]:
        trend = t["tag"].map(rz)
        gold = t["markt"] == "XAUUSD"
        blocked = gold & (((t["seite"] == "long") & (trend > 0)) | ((t["seite"] == "short") & (trend < 0)))
        keep["V2"] = ~blocked
    if "V3" in VARIANTS[edge] and sd is not None:
        sign = np.where(t["seite"] == "long", 1.0, -1.0)
        against = (sign * sd) <= -SCORE_CUT
        keep["V3"] = ~(against.fillna(False) & (t["markt"] != "XAUUSD"))
    return keep


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) == 0:
        return {"n": 0}
    eq = r.cumsum()
    return {"n": int(len(r)), "avg_r": round(float(r.mean()), 3), "sum_r": round(float(r.sum()), 1),
            "max_dd_r": round(float((eq - eq.cummax()).min()), 1),
            "t": round(float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))), 2) if len(r) > 2 else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos"], default="is")
    args = ap.parse_args()
    LOCK.register_split(*SPLIT)
    if args.stage == "is":
        LOCK.log_trials(sum(len(v) for v in VARIANTS.values()), "V1 Stress (3 Edges), V2 Realzins (ASB, C2), V3 Score (C2)")
    trades = load_trades()
    days = pd.bdate_range("2009-01-02", SPLIT[3])
    stress, rz = stress_days(days), realzins_trend(days)
    res = {}
    for edge, t in trades.items():
        frame = t.set_index("tag", drop=False)
        frame = LOCK.is_only(frame) if args.stage == "is" else LOCK.oos_only(frame)
        frame = frame.reset_index(drop=True)
        sd = score_diff(frame) if "V3" in VARIANTS[edge] else None
        k = masks(edge, frame, stress, rz, sd)
        node = {"basis": stats(frame["r"])}
        for v, keep in k.items():
            node[v] = {"behalten": stats(frame.loc[keep, "r"]), "entfernt": stats(frame.loc[~keep, "r"])}
        res[edge] = node
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev[args.stage] = res
    prev["lock"], prev["versuche"] = LOCK.strategy, LOCK.trials
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    for edge, node in res.items():
        b = node["basis"]
        print(f"\n{edge.upper()} {args.stage}: Basis n {b.get('n')} Ø {b.get('avg_r')} Σ {b.get('sum_r')} DD {b.get('max_dd_r')} t {b.get('t')}")
        for v in VARIANTS[edge]:
            if v in node:
                k, e = node[v]["behalten"], node[v]["entfernt"]
                print(f"  {v}: behalten n {k.get('n')} Ø {k.get('avg_r')} Σ {k.get('sum_r')} DD {k.get('max_dd_r')} t {k.get('t')}"
                      f" | entfernt n {e.get('n')} Ø {e.get('avg_r')} Σ {e.get('sum_r')}")


if __name__ == "__main__":
    main()
