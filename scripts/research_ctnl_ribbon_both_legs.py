"""CTNL: Ribbon-Richtungsfilter fuer BEIDE Beine + Vergleich 2024-2026 (2026-09-24)

Drei Nutzerfragen nach Befund 15:
  (1) Hat der Ribbon nur auf ctnl_reversal einen Edge oder auch auf
      ctnl_continuation?
  (2) Wie sehen die Zahlen 2024-2026 aus -- Ribbon gegen alle bisher
      geprueften Optimierungsvarianten IM SELBEN Fenster?
  (3) (ausserhalb dieses Skripts) Wie liesse sich der Edge auf die eigene
      Handelslogik umbauen?

Zu (2) die Einordnung vorweg: ein Vergleich NUR auf 2024-2026 ist
in-sample fuer jede Variante, die auf der Gesamthistorie ausgewaehlt wurde
-- und 2024-2026 ist genau das Fenster, in dem die Strategie ohnehin
funktioniert (Befund 7a). Die Zahlen beantworten "wie haette sich das
zuletzt angefuehlt", NICHT "welche Variante ist besser". Fuer letzteres
bleibt der Anker-Walk-Forward ueber die Gesamthistorie zustaendig.
Beides wird ausgewiesen, damit der Unterschied sichtbar bleibt.
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

from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.ema_ribbon import compute_ribbon  # noqa: E402
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import (  # noqa: E402
    anchored_walk_forward,
    leg_trades,
    regime_feature,
    surface,
    to_live,
)

RISK_PCT = {"ctnl_reversal": 0.0015, "ctnl_continuation": 0.005}
JUNG = pd.Timestamp("2024-01-01")


def stats(r) -> dict:
    r = pd.Series(r).dropna()
    if r.empty:
        return {"trades": 0, "avg_r": float("nan"), "summe_r": 0.0,
                "profit_factor": float("nan"), "trefferquote": float("nan")}
    w, l = r[r > 0], r[r <= 0]
    return {"trades": int(len(r)), "avg_r": float(r.mean()), "summe_r": float(r.sum()),
            "trefferquote": float((r > 0).mean()),
            "profit_factor": float(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else float("nan")}


def ribbon_direction(h4: pd.DataFrame, d1: pd.DataFrame, w1: pd.DataFrame) -> pd.Series:
    """+1 wenn der Preis UEBER allen vier Ribbon-EMAs liegt, -1 wenn unter
    allen, sonst 0. Script-Defaults, keine Parametersuche."""
    rib = compute_ribbon(h4, d1, w1)
    idx = _utc_naive(rib.index)
    px = pd.Series(rib["close"].to_numpy(), index=idx)
    cols = ["ema_h4", "ema_d1_fast", "ema_d1_slow", "ema_w1"]
    stack = pd.DataFrame({c: pd.Series(rib[c].to_numpy(), index=idx) for c in cols}).dropna()
    above = px.reindex(stack.index) > stack.max(axis=1)
    below = px.reindex(stack.index) < stack.min(axis=1)
    return pd.Series(np.where(above, 1, np.where(below, -1, 0)), index=stack.index)


def mc(d: pd.DataFrame, risk_pct: float) -> dict:
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * risk_pct).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 250:
        return {}
    m = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = m["summary"] if isinstance(m, dict) and "summary" in m else m
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
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_ribbon_both_legs.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    d1, w1 = fetch_gold_d1(args.start, args.end), fetch_gold_w1(args.start, args.end)
    rib_dir = ribbon_direction(bars["h4"], d1, w1)
    print(f"Ribbon: {len(rib_dir)} H4-Punkte, "
          f"{(rib_dir == 1).mean():.1%} aufwaerts / {(rib_dir == -1).mean():.1%} abwaerts / "
          f"{(rib_dir == 0).mean():.1%} neutral")

    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    kw = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    result: dict = {"beine": {}}

    for leg in ("ctnl_reversal", "ctnl_continuation"):
        print(f"\n{'='*96}\n{leg}\n{'='*96}")
        rep = to_live(leg_trades(bars, leg, tp_r=tp[leg], sig_kwargs=kw[leg]), bar_src[leg])
        t = _utc_naive(rep["entry_time"])
        rep = rep.assign(
            rib=rib_dir.reindex(t, method="ffill").to_numpy(),
            eff=regime_feature(bar_src[leg]).reindex(t).to_numpy(),
        )
        eff_thr = rep["eff"].quantile(0.50)

        varianten = {
            "Baseline": rep,
            "nur long": rep[rep["direction"] == 1],
            "long + Effizienz": rep[(rep["direction"] == 1) & (rep["eff"] <= eff_thr)],
            "ribbon-konform": rep[((rep["direction"] == 1) & (rep["rib"] > 0)) |
                                  ((rep["direction"] == -1) & (rep["rib"] < 0))],
            "ribbon long-only": rep[(rep["direction"] == 1) & (rep["rib"] > 0)],
        }

        # --- Frage 1: hat der Ribbon hier ueberhaupt Signal?
        sh_dn = rep[(rep["direction"] == -1) & (rep["rib"] < 0)]["r"]
        sh_up = rep[(rep["direction"] == -1) & (rep["rib"] > 0)]["r"]
        lo_up = rep[(rep["direction"] == 1) & (rep["rib"] > 0)]["r"]
        lo_dn = rep[(rep["direction"] == 1) & (rep["rib"] < 0)]["r"]
        print(f"\n  Ribbon-Trennschaerfe (Gesamthistorie)")
        print(f"    {'':22} {'n':>6} {'ØR':>9} {'ΣR':>9}")
        for name, r in (("SHORT im Abwaertstrend", sh_dn), ("SHORT im Aufwaertstrend", sh_up),
                        ("LONG im Aufwaertstrend", lo_up), ("LONG im Abwaertstrend", lo_dn)):
            st = stats(r)
            print(f"    {name:22} {st['trades']:>6} {st['avg_r']:>+9.3f} {st['summe_r']:>+9.1f}")
        result.setdefault("beine", {})[leg] = {"trennschaerfe": {
            "short_abwaerts": stats(sh_dn), "short_aufwaerts": stats(sh_up),
            "long_aufwaerts": stats(lo_up), "long_abwaerts": stats(lo_dn)}}

        # --- Frage 2: Vergleich Gesamthistorie vs. 2024-2026
        print(f"\n  Variantenvergleich")
        print(f"    {'Variante':>18} | {'--- 2016-2026 ---':^32} | {'--- 2024-2026 ---':^32}")
        print(f"    {'':>18} | {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6} | {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
        vergleich = {}
        for name, d in varianten.items():
            voll = stats(d["r"])
            jung = stats(d[_utc_naive(d["entry_time"]) >= JUNG]["r"])
            vergleich[name] = {"voll": voll, "2024_2026": jung}
            print(f"    {name:>18} | {voll['trades']:>5} {voll['avg_r']:>+8.3f} {voll['summe_r']:>+8.1f} "
                  f"{voll['profit_factor']:>6.2f} | {jung['trades']:>5} {jung['avg_r']:>+8.3f} "
                  f"{jung['summe_r']:>+8.1f} {jung['profit_factor']:>6.2f}")
        result["beine"][leg]["vergleich"] = vergleich

        result["beine"][leg]["walkforward"] = anchored_walk_forward(
            varianten, "Baseline", f"{leg}: alle Varianten")

        print(f"\n  Monte Carlo ({RISK_PCT[leg]:.2%}/Trade, Gesamthistorie):")
        print(f"    {'Variante':>18} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
        result["beine"][leg]["monte_carlo"] = {}
        for name, d in varianten.items():
            m = mc(d, RISK_PCT[leg])
            if not m:
                print(f"    {name:>18} {'zu wenige Handelstage':>38}")
                continue
            result["beine"][leg]["monte_carlo"][name] = m
            print(f"    {name:>18} {m['median_maxdd_pct']:>8.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
                  f"{m['median_return_pct']:>8.1f}% {m['median_sharpe']:>8.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
