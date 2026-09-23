"""CTNL: traegt die Short-Seite mit uebergeordneter Trendbestaetigung? (2026-09-23)

Nutzerhypothese: "nicht der Edge ist das Problem, sondern fehlende
Bestaetigung des Trends im Higher und Lower Timeframe. Das Continuation-Modell
ist dafuer da, auf laengere Trends aufzuspringen, und das Reversal-Modell
greift an der naechsten groesseren Liquidity."

Befund 12 hat gezeigt, dass die Short-Schwaeche ein REGIME-Effekt ist (in
fallenden Gold-Jahren Ø R +0,116, in steigenden -0,390). Die Hypothese geht
einen Schritt weiter: wenn man den Trend RICHTIG bestimmt, sollten Shorts im
Abwaertstrend tragen -- dann waere Long-only die falsche Antwort und eine
Trendbestaetigung die richtige.

TEIL 1 -- Der direkte Test (billig, entscheidend)
Jeder Trade bekommt den HTF-Trendzustand zum EINSTIEGSZEITPUNKT, aus einem
mehrstufigen EMA-Stack auf H4, D1 und W1. Dann Kreuztabelle
Richtung x Trendzustand. Verdienen Shorts im bestaetigten Abwaertstrend,
ist die Hypothese gestuetzt.

TEIL 2 -- Die eingebauten Filter, die nie benutzt wurden
Die Reversal-Pipeline hat bereits:
  require_h4_trend_confirm (+ trend_confirm_indicator/trend_fast/trend_slow)
  require_ribbon_stretch   (+ d1_df/w1_df/ribbon_extension_atr_min)
  require_h1_inducement, require_magnitude, require_level_age
Die gesperrte REV_KWARGS nutzt KEINEN davon. Sie werden hier einzeln
zugeschaltet und durch denselben Anker-Walk-Forward geschickt wie jeder
andere Kandidat -- ein IS-Sieger ohne OOS-Bestaetigung wird berichtet und
verworfen (Muster aus Befund 9b, wo `ohne_ema_reject` in 8/8 Jahren IS-Sieger
war und OOS verlor).

ALLE ZAHLEN ZUSAETZLICH FUER 2024-2026 (Nutzerfrage).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))

from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import (  # noqa: E402
    anchored_walk_forward,
    leg_trades,
    surface,
    to_live,
)

RISK_PCT = {"ctnl_reversal": 0.0015, "ctnl_continuation": 0.005}
JUNG_START = pd.Timestamp("2024-01-01")


def stats(r: pd.Series) -> dict:
    r = pd.Series(r).dropna()
    if r.empty:
        return {"trades": 0, "avg_r": float("nan"), "summe_r": 0.0,
                "profit_factor": float("nan"), "trefferquote": float("nan")}
    w, l = r[r > 0], r[r <= 0]
    return {"trades": int(len(r)), "avg_r": float(r.mean()), "summe_r": float(r.sum()),
            "trefferquote": float((r > 0).mean()),
            "profit_factor": float(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else float("nan")}


# --------------------------------------------------------------- EMA-Stack


def ema_state(df: pd.DataFrame, fast: int, mid: int, slow: int) -> pd.Series:
    """+1 = sauberer Aufwaertsstapel, -1 = Abwaertsstapel, 0 = verschraenkt.

    Bewusst der STAPEL (fast>mid>slow) und nicht nur ein Kreuzen: ein
    einzelnes Kreuzen kippt in Seitwaertsphasen staendig, der Stapel verlangt,
    dass alle drei Ebenen dasselbe sagen. Nur rueckwaertsgerichtet, also zum
    Einstieg verfuegbar.
    """
    idx = _utc_naive(df.index)
    c = pd.Series(df["close"].to_numpy(), index=idx)
    f, m, s = (c.ewm(span=n, adjust=False).mean() for n in (fast, mid, slow))
    up = (f > m) & (m > s)
    dn = (f < m) & (m < s)
    return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=idx)


def attach_trend(rep: pd.DataFrame, bars: dict) -> pd.DataFrame:
    """H4-, D1- und W1-Trendzustand zum Einstiegszeitpunkt."""
    rep = rep.copy()
    t = _utc_naive(rep["entry_time"])
    for name, key, spans in (("h4", "h4", (20, 50, 200)),
                             ("d1", "h4", (120, 300, 1200)),   # ~D1-Aequivalent auf H4-Bars
                             ("w1", "h4", (600, 1500, 6000))):  # ~W1-Aequivalent
        st = ema_state(bars[key], *spans)
        rep[f"trend_{name}"] = st.reindex(t, method="ffill").to_numpy()
    # Gesamtbild: Summe der drei Ebenen (-3 .. +3)
    rep["trend_sum"] = rep[["trend_h4", "trend_d1", "trend_w1"]].sum(axis=1)
    return rep


def kreuztabelle(rep: pd.DataFrame, spalte: str, titel: str) -> dict:
    print(f"\n  {titel}")
    print(f"    {'Trendzustand':>16} | {'LONG n':>7} {'ØR':>8} {'ΣR':>8} | {'SHORT n':>8} {'ØR':>8} {'ΣR':>8}")
    out = {}
    for zustand in sorted(rep[spalte].dropna().unique()):
        sub = rep[rep[spalte] == zustand]
        lo, sh = sub[sub["direction"] == 1]["r"], sub[sub["direction"] == -1]["r"]
        sl, ss = stats(lo), stats(sh)
        out[str(zustand)] = {"long": sl, "short": ss}
        print(f"    {str(zustand):>16} | {sl['trades']:>7} {sl['avg_r']:>+8.3f} {sl['summe_r']:>+8.1f} "
              f"| {ss['trades']:>8} {ss['avg_r']:>+8.3f} {ss['summe_r']:>+8.1f}")
    return out


def mc_row(d: pd.DataFrame, risk_pct: float) -> dict:
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * risk_pct).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 250:
        return {}
    mc = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
    dd = s["max_drawdown_pct"]
    return {"median_maxdd_pct": float(np.median(dd)),
            "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
            "median_return_pct": float(np.median(s["total_return_pct"])),
            "median_sharpe": float(np.median(s["sharpe"]))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_mtf_trend.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    base_kw = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    base_tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    result: dict = {"beine": {}}

    for leg in ("ctnl_reversal", "ctnl_continuation"):
        print(f"\n{'='*92}\n{leg}\n{'='*92}")
        rep = to_live(leg_trades(bars, leg, tp_r=base_tp[leg], sig_kwargs=base_kw[leg]), bar_src[leg])
        rep = attach_trend(rep, bars)
        jung = rep[_utc_naive(rep["entry_time"]) >= JUNG_START]
        res: dict = {}

        # ---- Nutzerfrage: 2024-2026
        print(f"\n  ZEITRAUM-VERGLEICH")
        print(f"    {'Zeitraum':>14} {'Richtung':>9} {'n':>6} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
        for label, d in (("2016-2026", rep), ("2024-2026", jung)):
            for rname, rv in (("long", 1), ("short", -1)):
                s = stats(d[d["direction"] == rv]["r"])
                res.setdefault("zeitraum", {}).setdefault(label, {})[rname] = s
                print(f"    {label:>14} {rname:>9} {s['trades']:>6} {s['avg_r']:>+8.3f} "
                      f"{s['summe_r']:>+8.1f} {s['profit_factor']:>6.2f}")

        # ---- TEIL 1: traegt short im bestaetigten Abwaertstrend?
        res["kreuz_h4"] = kreuztabelle(rep, "trend_h4", "Richtung x H4-EMA-Stapel (20/50/200), 2016-2026")
        res["kreuz_sum"] = kreuztabelle(rep, "trend_sum", "Richtung x Summe H4+D1+W1 (-3..+3), 2016-2026")
        if len(jung) > 30:
            res["kreuz_sum_jung"] = kreuztabelle(jung, "trend_sum", "dasselbe, nur 2024-2026")

        # ---- Die Kernfrage in einer Zahl
        sh_dn = rep[(rep["direction"] == -1) & (rep["trend_sum"] < 0)]["r"]
        sh_up = rep[(rep["direction"] == -1) & (rep["trend_sum"] > 0)]["r"]
        s_dn, s_up = stats(sh_dn), stats(sh_up)
        res["kernfrage"] = {"short_im_abwaertstrend": s_dn, "short_im_aufwaertstrend": s_up}
        print(f"\n  KERNFRAGE -- traegt die Short-Seite mit Trendbestaetigung?")
        print(f"    short bei trend_sum < 0 (Abwaerts): n={s_dn['trades']:<5} Ø R {s_dn['avg_r']:+.3f}  "
              f"ΣR {s_dn['summe_r']:+.1f}  PF {s_dn['profit_factor']:.2f}")
        print(f"    short bei trend_sum > 0 (Aufwaerts): n={s_up['trades']:<5} Ø R {s_up['avg_r']:+.3f}  "
              f"ΣR {s_up['summe_r']:+.1f}  PF {s_up['profit_factor']:.2f}")

        # ---- Varianten + Walk-Forward
        varianten = {
            "Baseline (beide)": rep,
            "nur long": rep[rep["direction"] == 1],
            "trendkonform": rep[((rep["direction"] == 1) & (rep["trend_sum"] > 0)) |
                                ((rep["direction"] == -1) & (rep["trend_sum"] < 0))],
            "trendkonform H4": rep[((rep["direction"] == 1) & (rep["trend_h4"] > 0)) |
                                   ((rep["direction"] == -1) & (rep["trend_h4"] < 0))],
            "gegen den Trend": rep[((rep["direction"] == 1) & (rep["trend_sum"] < 0)) |
                                   ((rep["direction"] == -1) & (rep["trend_sum"] > 0))],
        }
        res["flaeche"] = surface(varianten, f"{leg}: Trendbestaetigung")
        res["walkforward"] = anchored_walk_forward(varianten, "Baseline (beide)", f"{leg}: Trendbestaetigung")

        print(f"\n  Monte Carlo ({RISK_PCT[leg]:.2%}/Trade):")
        print(f"    {'Variante':>18} {'MedMaxDD':>10} {'P(>6%)':>8} {'MedReturn':>11} {'Sharpe':>8}")
        res["monte_carlo"] = {}
        for name, d in varianten.items():
            m = mc_row(d, RISK_PCT[leg])
            if not m:
                continue
            res["monte_carlo"][name] = m
            print(f"    {name:>18} {m['median_maxdd_pct']:>9.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
                  f"{m['median_return_pct']:>10.1f}% {m['median_sharpe']:>8.2f}")

        result["beine"][leg] = res

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
