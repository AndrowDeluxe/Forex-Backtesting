"""Edelmetalle HTF -- Score-Bausteine + Makro-Indikatoren auf 4-26 Wochen (Gold, Silber, Platin).

Plan freigegeben 18.11.2026 (knowledge/_handoff/2026-11-18_1630_edelmetalle-htf-backtest.md), Lock `metals_htf_v1`,
Vorab-Registrierung fusion_lab/metals_htf/spec.py (Commit 56a49a99).

    python scripts/research_metals_htf.py --stage data        # Rohdaten laden (fusion_lab.metals_htf.data)
    python scripts/research_metals_htf.py --stage ic          # Stufe 1: Einzel-IC, Kandidaten nur aus IS
    python scripts/research_metals_htf.py --stage regime      # Stufe 2: Drittel-Regel je Kandidat + Kontrollen
    python scripts/research_metals_htf.py --stage composite   # Stufe 3: Komposit vs. Screener 1.0/1.1 vs. nur Trend
    python scripts/research_metals_htf.py --stage filter      # Stufe 4: Bias als Veto auf ASB, CTNL, C2 (Gold)
    python scripts/research_metals_htf.py --stage robust      # Stufe 5: Jahre, Bootstrap, MC-DD, Nachbarschaft, DSR
    python scripts/research_metals_htf.py --stage all

Ergebnisse: fusion_lab/data/metals_htf/results/*.csv. Der Tresor bleibt zu (nur nach freeze + Nutzerfreigabe).
"""

from __future__ import annotations

import argparse
import sys
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from fusion_lab.metals_htf import backtest as B, features as F  # noqa: E402
from fusion_lab.metals_htf.spec import (COST_BPS, FEATURES, HORIZONS, IS_SUB, LOCK_NAME, LOOKBACKS, METALS,  # noqa: E402
                                        RANDOM_PCT_MIN, SPLIT, SWAP_PA, T_MIN, applicable, name, variants)
from research_lock import Lock, deflated_sharpe  # noqa: E402

warnings.filterwarnings("ignore")
LOCK = Lock(LOCK_NAME)
OUT = ROOT / "fusion_lab" / "data" / "metals_htf" / "results"
IS_END, OOS_END = pd.Timestamp(SPLIT[1]), pd.Timestamp(SPLIT[2])


@lru_cache(maxsize=1)
def frame() -> dict:
    b = F.build()
    b["o"] = F.oriented(b["raw"])
    b["R"] = F.returns(b["px"])
    return b


def _cut(s: pd.Series, start, end, h: int = 0) -> pd.Series:
    """Zeitraum [start, end], bei Forward-Renditen nur Wochen, deren Ziel t+h noch im Zeitraum liegt."""
    s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    return s[s.index + pd.Timedelta(weeks=h) <= pd.Timestamp(end)] if h else s


def periods() -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    return {"IS": (pd.Timestamp(SPLIT[0]), IS_END), "OOS": (IS_END + pd.Timedelta(days=1), OOS_END)}


def save(df: pd.DataFrame, fname: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / fname
    df.to_csv(p, index=False)
    return p


# ------------------------------------------------------------------ Stufe 1: IC

def stage_ic() -> pd.DataFrame:
    f = frame()
    rows = []
    for feat, L in variants():
        nm = name(feat, L)
        for m in METALS:
            if not applicable(feat, m):
                continue
            sig = f["o"][nm][m]
            for h in HORIZONS:
                fwd = f["R"][h][m]
                row = {"merkmal": feat, "L": L, "name": nm, "metall": m, "h": h, "info": bool(FEATURES[feat].get("info"))}
                is_ = B.ic(_cut(sig, SPLIT[0], IS_END, h), _cut(fwd, SPLIT[0], IS_END, h), h)
                row.update({"IS_n": is_["n"], "IS_ic": is_["ic"], "IS_t": is_["t"]})
                for i, (a, e) in enumerate(IS_SUB, 1):
                    x = B.ic(_cut(sig, a, e, h), _cut(fwd, a, e, h), h)
                    row.update({f"IS{i}_ic": x["ic"], f"IS{i}_n": x["n"]})
                oo = B.ic(_cut(LOCK.oos_only(sig), IS_END, OOS_END, h), _cut(LOCK.oos_only(fwd), IS_END, OOS_END, h), h)
                row.update({"OOS_n": oo["n"], "OOS_ic": oo["ic"], "OOS_t": oo["t"]})
                rows.append(row)
    res = pd.DataFrame(rows)
    n = int((~res["info"]).sum())
    LOCK.log_trials(n, "Stufe 1: IC je Merkmal x Lookback x Metall x Horizont (IS)")

    # Kandidaten-Regel (vorab registriert): IS-t >= 2 mit erwartetem Vorzeichen, IC > 0 in beiden IS-Teilzeiten
    # (soweit vorhanden), und gleiches Vorzeichen bei >= min(2, anwendbare Metalle) Metallen (gleiches L, h).
    pos = res[~res["info"]].groupby(["name", "h"]).apply(
        lambda g: pd.Series({"n_pos": int((g["IS_ic"] > 0).sum()), "n_app": len(g)})).reset_index()
    res = res.merge(pos, on=["name", "h"], how="left")
    sub_ok = ((res["IS1_ic"] > 0) | res["IS1_ic"].isna()) & ((res["IS2_ic"] > 0) | res["IS2_ic"].isna())
    res["kandidat"] = (~res["info"]) & (res["IS_t"] >= T_MIN) & (res["IS_ic"] > 0) & sub_ok & \
        (res["n_pos"] >= np.minimum(2, res["n_app"]))
    save(res, "stage1_ic.csv")
    k = res[res["kandidat"]].sort_values("IS_t", ascending=False)
    # je (Merkmal, Metall) das L mit dem hoechsten IS-t -> einziger optimierter Punkt
    best = k.sort_values("IS_t", ascending=False).drop_duplicates(["merkmal", "metall"])
    save(best, "stage1_kandidaten.csv")
    print(f"Stufe 1: {n} gezaehlte Varianten, {len(k)} Kandidaten-Zeilen, {len(best)} Kandidaten (Merkmal x Metall)")
    cols = ["name", "metall", "h", "IS_ic", "IS_t", "IS1_ic", "IS2_ic", "n_pos", "OOS_ic", "OOS_t"]
    print(best[cols].round(3).to_string(index=False) if len(best) else "  keine Kandidaten")
    # Uebersicht bestes |t| je Merkmal x Metall (auch ohne Kandidat), damit die Gegenrichtung sichtbar wird
    ov = res[~res["info"]].loc[res[~res["info"]].groupby(["merkmal", "metall"])["IS_t"].apply(lambda s: s.abs().idxmax())]
    save(ov, "stage1_uebersicht.csv")
    return res


# ------------------------------------------------------------------ Stufe 2: Regime

def regime_row(sig: pd.Series, m: str, label: dict, pos: pd.Series | None = None) -> dict:
    f = frame()
    r1 = f["R"][1][m]
    pos = B.positions(sig) if pos is None else pos
    row = dict(label)
    for per, (a, e) in periods().items():
        p, r = _cut(pos, a, e, 1), _cut(r1, a, e, 1)
        if per == "OOS":
            p, r = LOCK.oos_only(p), LOCK.oos_only(r)
        pr = B.pnl(p, r, COST_BPS[m])
        st = B.stats(pr, p)
        row.update({f"{per}_{k}": v for k, v in st.items()})
        row[f"{per}_long_sharpe"] = round(B.sharpe(B.pnl(p.clip(lower=0), r, COST_BPS[m])), 3)
        row[f"{per}_short_sharpe"] = round(B.sharpe(B.pnl(p.clip(upper=0), r, COST_BPS[m])), 3)
        al = B.pnl(pd.Series(1.0, index=r.index), r, COST_BPS[m])
        row[f"{per}_immerlong_sharpe"] = round(B.sharpe(al), 3)
        fab = _cut(B.faber_positions(f["raw"][("faber", None)][m]), a, e, 1)
        row[f"{per}_faber_sharpe"] = round(B.sharpe(B.pnl(fab, r, COST_BPS[m])), 3)
        sims = B.random_timing(p, r, COST_BPS[m])
        sr = B.sharpe(pr)
        row[f"{per}_zufall_pct"] = round(float((sims < sr).mean() * 100), 1) if np.isfinite(sr) else np.nan
    row["erfolg"] = all(
        (row.get(f"{per}_sharpe", np.nan) > row.get(f"{per}_immerlong_sharpe", np.inf))
        and (row.get(f"{per}_zufall_pct", 0) >= RANDOM_PCT_MIN) for per in ("IS", "OOS"))
    return row


def stage_regime() -> pd.DataFrame:
    f = frame()
    k = pd.read_csv(OUT / "stage1_kandidaten.csv")
    rows = []
    for _, c in k.iterrows():
        nm = name(c["merkmal"], None if pd.isna(c["L"]) else int(c["L"]))
        rows.append(regime_row(f["o"][nm][c["metall"]], c["metall"],
                               {"merkmal": c["merkmal"], "L": c["L"], "name": nm, "metall": c["metall"]}))
    res = pd.DataFrame(rows)
    if len(res):
        LOCK.log_trials(len(res), "Stufe 2: Regime-Regel je Kandidat")
    save(res, "stage2_regime.csv")
    print(f"Stufe 2: {len(res)} Kandidaten, Erfolg (schlaegt immer long + Zufall >= {RANDOM_PCT_MIN} in IS und OOS): "
          f"{int(res['erfolg'].sum()) if len(res) else 0}")
    if len(res):
        cols = ["name", "metall", "IS_sharpe", "IS_immerlong_sharpe", "IS_faber_sharpe", "IS_zufall_pct",
                "IS_long_sharpe", "IS_short_sharpe", "OOS_sharpe", "OOS_immerlong_sharpe", "OOS_faber_sharpe",
                "OOS_zufall_pct", "OOS_long_sharpe", "OOS_short_sharpe", "erfolg"]
        print(res[cols].to_string(index=False))
    return res


# ------------------------------------------------------------------ Stufe 3: Komposit + Screener-Nachbau

def _logistic(z: pd.Series, scale: float) -> pd.Series:
    return 100.0 / (1.0 + np.exp(-z / scale))


def screener_score(m: str, weights: dict[str, float]) -> pd.Series:
    """Screener-Score (scoring.commodities) als Wochenreihe; Bausteine wie dort, fehlend = 50."""
    f = frame()
    d = f["daily"][m]
    W = lambda col: F.weekly(d[col], f["grid"])  # noqa: E731
    y = F.D.load("yf")["dbc_close"].dropna()
    dbc63 = F.weekly((y / y.shift(63) - 1) * 100, f["grid"]).fillna(0.0)
    comp = pd.DataFrame(index=f["grid"])
    comp["trend"] = W("trend")
    comp["momentum"] = _logistic(W("momentum"), 0.5)
    comp["rel_staerke"] = _logistic((W("ret_63d") - dbc63) / 10.0, 1.0)
    comp["cot"] = 100.0 - f["raw"][("cot_mit", None)][m] * 100.0
    comp["abstand_hoch"] = W("lage_52w") * 100.0
    comp = comp.clip(0, 100).fillna(50.0)
    w = pd.Series(weights, dtype=float)
    score = (comp[w.index] * w).sum(axis=1) / w.sum()
    return score.where(f["px"][m].notna())


SCREENER = {"Screener 1.0 (COT contra 20)": {"trend": 30, "momentum": 25, "rel_staerke": 15, "cot": 20, "abstand_hoch": 10},
            "Screener 1.1 (COT 0)": {"trend": 30, "momentum": 25, "rel_staerke": 15, "cot": 0, "abstand_hoch": 10}}


def score_positions(score: pd.Series, hi: float = 65, lo: float = 35) -> pd.Series:
    return pd.Series(np.where(score >= hi, 1.0, np.where(score <= lo, -1.0, 0.0)), index=score.index)


def composite(m: str) -> tuple[pd.Series | None, list[str], str]:
    """Gleichgewichteter Mittelwert der Ueberlebenden aus Stufe 2 (sonst Stufe-1-Kandidaten), neu perzentiliert."""
    f = frame()
    s2 = pd.read_csv(OUT / "stage2_regime.csv") if (OUT / "stage2_regime.csv").stat().st_size > 2 else pd.DataFrame()
    names, basis = [], "Ueberlebende Stufe 2"
    if len(s2):
        names = list(s2[(s2["metall"] == m) & (s2["erfolg"])]["name"])
    if not names:
        k = pd.read_csv(OUT / "stage1_kandidaten.csv")
        names, basis = list(k[k["metall"] == m]["name"]), "Kandidaten Stufe 1 (keine Ueberlebenden)"
    if not names:
        return None, [], "keine Merkmale"
    raw = pd.concat([f["o"][n][m] for n in names], axis=1).mean(axis=1, skipna=False)
    return F.rolling_pct(raw), names, basis


def stage_composite() -> pd.DataFrame:
    f = frame()
    rows = []
    for m in METALS:
        sig, names, basis = composite(m)
        if sig is not None:
            rows.append(regime_row(sig, m, {"variante": "Komposit", "metall": m, "basis": basis,
                                            "merkmale": ";".join(names)}))
        for lab, w in SCREENER.items():
            rows.append(regime_row(None, m, {"variante": lab, "metall": m, "basis": "Gewichte vom 18.11."},
                                   pos=score_positions(screener_score(m, w))))
        tr = F.weekly(f["daily"][m]["trend"], f["grid"])
        rows.append(regime_row(None, m, {"variante": "nur Trend (>=75 long, <=25 short)", "metall": m,
                                         "basis": "trend_points"}, pos=score_positions(tr, 75, 25)))
    res = pd.DataFrame(rows)
    LOCK.log_trials(len(res), "Stufe 3: Komposit + Screener-Varianten")
    save(res, "stage3_komposit.csv")
    cols = ["variante", "metall", "IS_sharpe", "IS_immerlong_sharpe", "IS_zufall_pct", "IS_long_%", "IS_short_%",
            "OOS_sharpe", "OOS_immerlong_sharpe", "OOS_zufall_pct", "OOS_long_sharpe", "OOS_short_sharpe", "erfolg"]
    print(res[cols].to_string(index=False))
    return res


# ------------------------------------------------------------------ Stufe 4: Filter auf Live-Gold-Edges

def gold_bias() -> dict[str, pd.Series]:
    out = {}
    sig, names, basis = composite("GOLD")
    if sig is not None:
        out[f"Komposit ({basis})"] = B.positions(sig)
    for lab, w in SCREENER.items():
        out[lab] = score_positions(screener_score("GOLD", w))
    out["nur Trend"] = score_positions(F.weekly(frame()["daily"]["GOLD"]["trend"], frame()["grid"]), 75, 25)
    return out


def prior(series: pd.Series, tags: pd.Series) -> np.ndarray:
    """Wert vom letzten Freitag STRIKT vor dem Trade-Tag (Wochenwert steht erst zum Freitagsschluss fest)."""
    s = series.dropna()
    pos = s.index.searchsorted(pd.DatetimeIndex(tags), side="left") - 1
    return np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)


def macro_gate_pass(t: pd.DataFrame) -> np.ndarray:
    """Live-CTNL-Makro-Sperre (gold_smc_htf_ltf.macro_gate): kein Long bei MACRO <= 35, kein Short bei >= 65."""
    s = pd.read_parquet(ROOT / "fusion_lab" / "data" / "gold_confirm" / "score_frame.parquet",
                        columns=["MACRO"])["MACRO"].dropna() * 100
    v = prior(s, t["tag"])
    block = ((t["seite"].values > 0) & (v <= 35)) | ((t["seite"].values < 0) & (v >= 65))
    return ~block


def keep_vs_drop(t: pd.DataFrame, mask: np.ndarray, n_rand: int = 2000, seed: int = 3) -> dict:
    out = {}
    rng = np.random.default_rng(seed)
    t = t.assign(k=mask).set_index("tag")
    for per, sl in (("IS", LOCK.is_only), ("OOS", LOCK.oos_only)):
        x = sl(t)
        k, d = x[x["k"]], x[~x["k"]]
        out.update({f"{per}_n_beh": len(k), f"{per}_R_beh": round(k["r"].mean(), 3) if len(k) else np.nan,
                    f"{per}_n_weg": len(d), f"{per}_R_weg": round(d["r"].mean(), 3) if len(d) else np.nan})
        if 0 < len(k) < len(x):
            sims = np.array([rng.choice(x["r"].values, len(k), replace=False).mean() for _ in range(n_rand)])
            out[f"{per}_p_zufall"] = round(float((sims >= k["r"].mean()).mean()), 3)
    return out


def ctnl_live_trades() -> pd.DataFrame:
    """Live-Set CTNL-Reversal (Ribbon + Spike >= Schwelle, ab 2016) -- enthaelt den Ribbon-Trendfilter schon."""
    from gold_smc_htf_ltf.spike_gate import SPIKE_MIN_ATR
    d = pd.read_pickle(ROOT / "fusion_lab" / "data" / "gold_confirm" / "results" / "ctnl_live_set.pkl")
    d = d[d["spike"] >= SPIKE_MIN_ATR]
    return pd.DataFrame({"tag": pd.to_datetime(d["et"]).dt.normalize(), "seite": d["direction"].astype(int),
                         "r": d["r"]})


def stage_filter() -> pd.DataFrame:
    import research_gold_confirm as rgc   # Trade-Listen wiederverwenden (eigener keep_vs_drop mit metals-Lock)
    edges = {"ASB": rgc.asb_trades, "C2": rgc.c2_trades, "CTNL": rgc.ctnl_trades, "CTNL-Live": ctnl_live_trades}
    bias = gold_bias()
    rows = []
    for en, fn in edges.items():
        t = fn()[["tag", "seite", "r"]].copy()
        t["tag"] = pd.to_datetime(t["tag"]).dt.normalize()
        t = t.dropna(subset=["r"]).sort_values("tag").reset_index(drop=True)
        basis = "alle Trades"
        if en.startswith("CTNL"):
            t = t[macro_gate_pass(t)].reset_index(drop=True)     # live Makro-Sperre schon herausgerechnet
            basis = "nach Live-Makro-Sperre"
        rows.append({"edge": en, "bias": "-", "variante": "Basis", "basis": basis,
                     **keep_vs_drop(t, np.ones(len(t), bool))})
        for bn, b in bias.items():
            d = prior(b, t["tag"])
            ok = ~np.isnan(d)
            tt, dd = t[ok].reset_index(drop=True), d[ok]
            masks = {"kein Trade gegen": ~((dd != 0) & (dd == -tt["seite"].values)),
                     "nur mit": dd == tt["seite"].values}
            for vn, mk in masks.items():
                rows.append({"edge": en, "bias": bn, "variante": vn, "basis": basis, **keep_vs_drop(tt, mk)})
    res = pd.DataFrame(rows)
    LOCK.log_trials(int((res["variante"] != "Basis").sum()), "Stufe 4: Bias-Veto auf ASB/C2/CTNL")
    save(res, "stage4_filter.csv")
    cols = ["edge", "bias", "variante", "IS_n_beh", "IS_R_beh", "IS_n_weg", "IS_R_weg", "IS_p_zufall",
            "OOS_n_beh", "OOS_R_beh", "OOS_n_weg", "OOS_R_weg", "OOS_p_zufall"]
    print(res.reindex(columns=cols).to_string(index=False))
    return res


# ------------------------------------------------------------------ Stufe 5: Robustheit

def robust_targets() -> list[tuple[str, str, pd.Series, str | None]]:
    """(Label, Metall, Positionsreihe, Merkmal fuer Lookback-Nachbarschaft oder None)."""
    f = frame()
    out = []
    s2 = pd.read_csv(OUT / "stage2_regime.csv") if (OUT / "stage2_regime.csv").stat().st_size > 2 else pd.DataFrame()
    for _, c in (s2[s2["erfolg"]] if len(s2) else s2).iterrows():
        out.append((c["name"], c["metall"], B.positions(f["o"][c["name"]][c["metall"]]), c["merkmal"]))
    for m in METALS:
        sig, names, _ = composite(m)
        if sig is not None:
            out.append(("Komposit", m, B.positions(sig), None))
        for lab, w in SCREENER.items():
            out.append((lab, m, score_positions(screener_score(m, w)), None))
        out.append(("immer long", m, pd.Series(1.0, index=f["grid"]), None))
    return out


def stage_robust() -> pd.DataFrame:
    f = frame()
    trials = LOCK.trials
    rows, years = [], []
    a, e = pd.Timestamp(SPLIT[0]), OOS_END
    for lab, m, pos, feat in robust_targets():
        r1 = _cut(f["R"][1][m], a, e, 1)
        p = _cut(pos, a, e, 1)
        pr = B.pnl(p, r1, COST_BPS[m])
        sr_w = pr.mean() / pr.std(ddof=1)
        bs = B.block_bootstrap(pr, B.sharpe)
        dd = B.block_bootstrap(pr, B.max_dd)
        row = {"variante": lab, "metall": m, "sharpe_IS+OOS": round(B.sharpe(pr), 3),
               "sharpe_KI5": round(np.nanpercentile(bs, 5), 3), "sharpe_KI95": round(np.nanpercentile(bs, 95), 3),
               "maxDD_%": round(B.max_dd(pr) * 100, 1), "MC_DD95_%": round(np.nanpercentile(dd, 5) * 100, 1),
               "verzoegert_1W_sharpe": round(B.sharpe(B.pnl(p.shift(1).fillna(0), r1, COST_BPS[m])), 3),
               "swap3pa_sharpe": round(B.sharpe(B.pnl(p, r1, COST_BPS[m], swap_pa=SWAP_PA)), 3),
               "kosten_x2_sharpe": round(B.sharpe(B.pnl(p, r1, 2 * COST_BPS[m])), 3),
               "DSR": round(deflated_sharpe(float(sr_w), len(pr), max(trials, 1)), 3) if np.isfinite(sr_w) else np.nan,
               "trials": trials}
        if feat and FEATURES[feat]["lb"]:
            nb = {L: B.sharpe(B.pnl(_cut(B.positions(f["o"][name(feat, L)][m]), a, IS_END, 1),
                                    _cut(f["R"][1][m], a, IS_END, 1), COST_BPS[m])) for L in LOOKBACKS}
            al = B.sharpe(B.pnl(pd.Series(1.0, index=_cut(f["R"][1][m], a, IS_END, 1).index),
                                _cut(f["R"][1][m], a, IS_END, 1), COST_BPS[m]))
            row.update({f"IS_sharpe_L{L}": round(v, 3) for L, v in nb.items()})
            row["nachbarschaft_ok"] = sum(v > al for v in nb.values()) >= 2
        rows.append(row)
        yr = pr.groupby(pr.index.year).sum() * 100
        years.append(pd.Series(yr.round(1), name=f"{lab} | {m}"))
    res = pd.DataFrame(rows)
    save(res, "stage5_robust.csv")
    jt = pd.DataFrame(years).T
    jt.index.name = "jahr"
    OUT.mkdir(parents=True, exist_ok=True)
    jt.to_csv(OUT / "stage5_jahre.csv")
    print(res.to_string(index=False))
    return res


STAGES = {"ic": stage_ic, "regime": stage_regime, "composite": stage_composite, "filter": stage_filter,
          "robust": stage_robust}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["data", *STAGES, "all"])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 250)
    if a.stage == "data":
        from fusion_lab.metals_htf import data
        data.main()
        return
    LOCK.register_split(*SPLIT)   # idempotent; bricht ab, falls jemand den Split veraendert hat
    for s in (STAGES if a.stage == "all" else [a.stage]):
        print(f"\n===== Stufe {s} =====")
        STAGES[s]()


if __name__ == "__main__":
    main()
