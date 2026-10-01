"""CTNL Reversal: Haltedauer, Ein-/Ausstiegszeiten und Parallelitaets-Deckel
(2026-10-01)

Zwei Nutzerfragen nach dem Rollout des Ribbon-Gates:

  (1) "Backteste CTNL ohne die Begrenzung der Haltedauer -- der Trade von
      gestern waere heute sauber weitergelaufen." Dazu die Verteilung nach
      Haltedauer sowie Ein- und Ausstiegszeiten.
  (2) "Pruefe die Risikobegrenzung auf drei Trades -- ist die mit der
      Risikohalbierung noch noetig?" Gemeint ist REV_MAX_CONCURRENT = 3:
      das Ribbon-Gate verwirft rund 60 % der Signale und senkt den
      Monte-Carlo-Median-Drawdown von -15,63 % auf -5,63 %. Die Frage ist
      also, ob der Deckel noch bindet oder nur noch Trades kostet.

ALLES AUF DEM HEUTIGEN BETRIEBSPUNKT: gesperrte Config + Ribbon-Gate,
gemessene Kosten 2,01 bps, Lag 1, R-Detektor 0,50R. Der Ribbon wird mit
denselben Script-Defaults gelesen wie live (gold_smc_htf_ltf/ribbon_gate.py).

WARUM "OHNE HALTEDAUER" NICHT NUR EINE ZAHL IST
max_hold_bars ist heute 96*4 = 384 M15-Bars = 96 Stunden. Faellt der Deckel,
aendert sich nicht nur das Ergebnis einzelner Trades, sondern auch die
BELEGUNG: ein laenger laufender Trade blockiert unter REV_MAX_CONCURRENT
einen Platz, den sonst ein neues Signal bekommen haette. Beide Effekte
werden getrennt ausgewiesen -- sonst haelt man eine Belegungsaenderung fuer
einen Edge-Gewinn.
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

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h4  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from gold_smc_htf_ltf.ribbon_gate import ribbon_direction  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, surface, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import stats  # noqa: E402

RISK = 0.0015           # FK-Reversal-Split, live_signal.py
HEUTE_MAXHOLD = 96 * 4  # 384 M15-Bars = 96 Stunden
HEUTE_CONCURRENT = 3


def mc(d: pd.DataFrame) -> dict:
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * RISK).resample("D").sum()
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
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_haltedauer_zeiten.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    rib = ribbon_direction(fetch_gold_h4(args.start, args.end), fetch_gold_d1(args.start, args.end))
    r_idx = pd.to_datetime(rib.index)
    rib.index = r_idx.tz_convert(None) if r_idx.tz is not None else r_idx
    sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)

    def bauen(max_hold, max_concurrent):
        from strategy.backtest import BacktestConfig
        cfg = BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False,
                             take_profit_r=5.0, max_hold_bars=max_hold)
        tr = _cap_concurrent(simulate_trades_concurrent(sig, cfg), max_concurrent)
        rep = to_live(tr, bars["m15"])
        t = _utc_naive(rep["entry_time"])
        rep = rep.assign(rib=rib.reindex(t, method="ffill").to_numpy())
        gate = rep[((rep["direction"] == 1) & (rep["rib"] > 0)) |
                   ((rep["direction"] == -1) & (rep["rib"] < 0))]
        # Haltedauer + Zeiten aus der Roh-Trade-Tabelle nachziehen
        roh = tr.set_index(tr["entry_time"].map(lambda x: _utc_naive(pd.Series([x]))[0]))
        return gate, tr

    result: dict = {}

    # ---------------- A) Haltedauer-Sweep
    print(f"{'='*100}\nA) max_hold-Sweep (heute: {HEUTE_MAXHOLD} Bars = {HEUTE_MAXHOLD*15/60:.0f} h), "
          f"max_concurrent={HEUTE_CONCURRENT}, ribbon-gefiltert\n{'='*100}")
    kandidaten = {"96 h (heute)": HEUTE_MAXHOLD, "24 h": 96, "48 h": 192, "192 h": 768,
                  "384 h": 1536, "ohne Grenze": None}
    varianten, rohe = {}, {}
    print(f"  {'Variante':>14} {'Trades':>7} {'ØR':>8} {'ΣR':>8} {'PF':>6} {'Treffer':>8} "
          f"{'Ø Haltedauer':>13} {'Median':>8}")
    for name, mh in kandidaten.items():
        g, tr = bauen(mh, HEUTE_CONCURRENT)
        varianten[name], rohe[name] = g, tr
        s = stats(g["r"])
        hold_h = (tr["hold_bars"] * 15 / 60)
        print(f"  {name:>14} {s['trades']:>7} {s['avg_r']:>+8.3f} {s['summe_r']:>+8.1f} "
              f"{s['profit_factor']:>6.2f} {s['trefferquote']:>7.1%} "
              f"{hold_h.mean():>11.1f} h {hold_h.median():>6.1f} h")
    result["maxhold_flaeche"] = surface(varianten, "ctnl_reversal: max_hold")
    result["maxhold_wf"] = anchored_walk_forward(varianten, "96 h (heute)", "ctnl_reversal: max_hold")

    print(f"\n  Monte Carlo ({RISK:.2%}/Trade):")
    print(f"    {'Variante':>14} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    result["maxhold_mc"] = {}
    for name, g in varianten.items():
        m = mc(g)
        if not m:
            continue
        result["maxhold_mc"][name] = m
        print(f"    {name:>14} {m['median_maxdd_pct']:>8.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
              f"{m['median_return_pct']:>8.1f}% {m['median_sharpe']:>8.2f}")

    # ---------------- B) Exit-Gruende und Haltedauer je Ausgang
    print(f"\n{'='*100}\nB) Wohin laufen die Trades? (heute vs. ohne Haltedauer-Grenze)\n{'='*100}")
    result["exitgruende"] = {}
    for name in ("96 h (heute)", "ohne Grenze"):
        tr = rohe[name]
        print(f"\n  {name}: {len(tr)} Trades")
        print(f"    {'Grund':>12} {'n':>6} {'Anteil':>7} {'ØR':>8} {'Ø Haltedauer':>13}")
        d = {}
        for grund, sub in tr.groupby("exit_reason"):
            d[str(grund)] = {"n": int(len(sub)), "anteil": float(len(sub)/len(tr)),
                             "avg_r": float(sub["r_multiple"].mean()),
                             "hold_h": float((sub["hold_bars"]*15/60).mean())}
            print(f"    {str(grund):>12} {len(sub):>6} {len(sub)/len(tr):>6.1%} "
                  f"{sub['r_multiple'].mean():>+8.3f} {(sub['hold_bars']*15/60).mean():>11.1f} h")
        result["exitgruende"][name] = d

    # Haltedauer: Gewinner gegen Verlierer
    print(f"\n  Haltedauer Gewinner vs. Verlierer (ohne Grenze):")
    tr = rohe["ohne Grenze"]
    for label, sub in (("Gewinner", tr[tr["r_multiple"] > 0]), ("Verlierer", tr[tr["r_multiple"] <= 0])):
        h = sub["hold_bars"] * 15 / 60
        print(f"    {label:>10} n={len(sub):>4}  p25 {h.quantile(.25):>6.1f} h | Median {h.median():>6.1f} h "
              f"| p75 {h.quantile(.75):>6.1f} h | p95 {h.quantile(.95):>7.1f} h | max {h.max():>7.1f} h")

    # ---------------- C) Ein- und Ausstiegszeiten
    print(f"\n{'='*100}\nC) Ein- und Ausstiegszeiten (UTC, ribbon-gefiltert, heutige Config)\n{'='*100}")
    g = varianten["96 h (heute)"]
    tr = rohe["96 h (heute)"]
    ein = _utc_naive(tr["entry_time"]).dt.hour
    aus = _utc_naive(tr["exit_time"]).dt.hour
    r = tr["r_multiple"]
    result["zeiten"] = {}
    for label, stunden in (("Einstiegsstunde", ein), ("Ausstiegsstunde", aus)):
        print(f"\n  {label}:")
        print(f"    {'Std':>4} {'n':>5} {'ØR':>8} {'ΣR':>8}")
        d = {}
        for h in sorted(stunden.unique()):
            sub = r[stunden == h]
            d[int(h)] = {"n": int(len(sub)), "avg_r": float(sub.mean()), "summe_r": float(sub.sum())}
            print(f"    {h:>4} {len(sub):>5} {sub.mean():>+8.3f} {sub.sum():>+8.1f}")
        result["zeiten"][label] = d

    # ---------------- D) Braucht es den 3er-Deckel noch?
    print(f"\n{'='*100}\nD) Parallelitaets-Deckel: bindet REV_MAX_CONCURRENT=3 noch?\n{'='*100}")
    conc = {}
    print(f"  {'Deckel':>12} {'Trades':>7} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
    for c in (1, 2, 3, 5, 99):
        g, _ = bauen(HEUTE_MAXHOLD, c)
        conc[f"max {c}" if c < 99 else "ohne Deckel"] = g
        s = stats(g["r"])
        print(f"  {('max '+str(c)) if c<99 else 'ohne Deckel':>12} {s['trades']:>7} {s['avg_r']:>+8.3f} "
              f"{s['summe_r']:>+8.1f} {s['profit_factor']:>6.2f}")
    result["concurrent_flaeche"] = surface(conc, "ctnl_reversal: max_concurrent")
    print(f"\n  Monte Carlo ({RISK:.2%}/Trade):")
    print(f"    {'Deckel':>12} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    result["concurrent_mc"] = {}
    for name, g in conc.items():
        m = mc(g)
        if not m:
            continue
        result["concurrent_mc"][name] = m
        print(f"    {name:>12} {m['median_maxdd_pct']:>8.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
              f"{m['median_return_pct']:>8.1f}% {m['median_sharpe']:>8.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
