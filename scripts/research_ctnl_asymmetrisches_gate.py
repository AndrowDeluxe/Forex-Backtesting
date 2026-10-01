"""CTNL: laesst sich der Ribbon asymmetrisch anwenden -- und taugt ein
Meta-Modell, das zwischen "mit" und "ohne" umschaltet? (2026-10-01)

Nutzerfrage: "Kann man ein Modell bauen, das herausfiltert, wann der Ribbon
Sinn macht und wann ohne Ribbon sinnvoll ist? Oder das Edge separieren, um
das Beste aus beiden zu nutzen?"

DIE BEIDEN IDEEN SIND UNTERSCHIEDLICH SCHWER

(A) EDGE SEPARIEREN -- vielversprechend, kostet KEINEN Freiheitsgrad.
Die Trennschaerfe-Tabelle (Befund 16a) zeigt vier Felder, nicht zwei:

      long  im Aufwaertstrend  Ø R +0,842   <- Ribbon behaelt
      short im Abwaertstrend   Ø R +0,174   <- Ribbon behaelt
      short im Aufwaertstrend  Ø R -0,519   <- Ribbon verwirft, zu Recht
      long  im Abwaertstrend   Ø R +0,391   <- Ribbon verwirft, OBWOHL POSITIV

Das vierte Feld ist der Punkt: der Ribbon wirft einen profitablen Teil weg.
Eine ASYMMETRISCHE Regel (Longs immer, Shorts nur trendkonform) waere keine
neue Optimierung, sondern das Weglassen einer Einschraenkung, die die Daten
nie gestuetzt haben. Genau das wird hier geprueft.

(B) META-MODELL -- deutlich heikler, und das wird hier ehrlich ausgewiesen.
Ein Umschalter braucht eine Groesse, die VORHER sagt, ob gefiltert besser
ist. Das ist eine Vorhersage ZWEITER Ordnung auf denselben ~1.250 Trades,
auf denen schon die erste Ordnung gewaehlt wurde. Befund 16e ist dazu ein
direkter Gegenbeleg: derselbe Walk-Forward lieferte OOS +243,6 mit DREI
Kandidaten und nur +185,8 mit FUENF -- mehr Auswahl hat das Ergebnis
VERSCHLECHTERT. Trotzdem wird ein einfacher Umschalter mitgetestet, damit
die Frage eine Zahl bekommt statt einer Meinung.

Beides durch denselben Anker-Walk-Forward wie alles andere. Der
Kandidatenkreis bleibt bewusst klein (Befund 16e).
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
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h1, fetch_gold_h4, fetch_gold_m15  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from gold_smc_htf_ltf.ribbon_gate import ribbon_direction  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, surface, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import stats  # noqa: E402
from strategy.backtest import BacktestConfig  # noqa: E402

RISK = 0.0015
JUNG = pd.Timestamp("2024-01-01")


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
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_asymmetrisches_gate.json")
    args = ap.parse_args()

    V, B = args.start, args.end
    h4, h1, m15 = fetch_gold_h4(V, B), fetch_gold_h1(V, B), fetch_gold_m15(V, B)
    rib = ribbon_direction(h4, fetch_gold_d1(V, B))
    ri = pd.to_datetime(rib.index); rib.index = ri.tz_convert(None) if ri.tz is not None else ri

    sig = run_reversal(h4, h1, m15, **REV_KWARGS)
    cfg = BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False,
                         take_profit_r=5.0, max_hold_bars=96 * 4)
    tr = _cap_concurrent(simulate_trades_concurrent(sig, cfg), REV_MAX_CONCURRENT)
    rep = to_live(tr, m15)
    t = _utc_naive(rep["entry_time"])
    rep = rep.assign(rib=rib.reindex(t, method="ffill").to_numpy())
    rep = rep.dropna(subset=["rib"])

    L, S = rep["direction"] == 1, rep["direction"] == -1
    AUF, AB = rep["rib"] > 0, rep["rib"] < 0

    print(f"{'='*96}\nDie vier Felder einzeln (Gesamthistorie)\n{'='*96}")
    felder = {"long / Aufwaerts": rep[L & AUF], "long / Abwaerts": rep[L & AB],
              "long / neutral": rep[L & ~AUF & ~AB],
              "short / Abwaerts": rep[S & AB], "short / Aufwaerts": rep[S & AUF],
              "short / neutral": rep[S & ~AUF & ~AB]}
    print(f"  {'Feld':>20} {'n':>6} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
    result = {"felder": {}}
    for name, d in felder.items():
        s = stats(d["r"]); result["felder"][name] = s
        print(f"  {name:>20} {s['trades']:>6} {s['avg_r']:>+8.3f} {s['summe_r']:>+8.1f} {s['profit_factor']:>6.2f}")

    # ---- Kandidaten: bewusst klein gehalten (Befund 16e)
    varianten = {
        "ungefiltert": rep,
        "ribbon-konform (heute)": rep[(L & AUF) | (S & AB)],
        "A: long immer, short gefiltert": rep[L | (S & AB)],
        "B: nur Shorts im Aufwaerts weg": rep[~(S & AUF)],
    }

    print(f"\n{'='*96}\nA) Asymmetrisches Gate\n{'='*96}")
    print(f"  {'Variante':>32} | {'--- 2016-2026 ---':^30} | {'-- 2024-2026 --':^22}")
    print(f"  {'':>32} | {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>5} | {'n':>4} {'ØR':>8} {'PF':>5}")
    result["varianten"] = {}
    for name, d in varianten.items():
        v = stats(d["r"]); j = stats(d[_utc_naive(d["entry_time"]) >= JUNG]["r"])
        result["varianten"][name] = {"voll": v, "2024_2026": j}
        print(f"  {name:>32} | {v['trades']:>5} {v['avg_r']:>+8.3f} {v['summe_r']:>+8.1f} "
              f"{v['profit_factor']:>5.2f} | {j['trades']:>4} {j['avg_r']:>+8.3f} {j['profit_factor']:>5.2f}")

    result["walkforward"] = anchored_walk_forward(varianten, "ungefiltert",
                                                  "ctnl_reversal: asymmetrisches Gate")
    print(f"\n  Monte Carlo ({RISK:.2%}/Trade):")
    print(f"    {'Variante':>32} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    result["monte_carlo"] = {}
    for name, d in varianten.items():
        m = mc(d)
        if not m:
            continue
        result["monte_carlo"][name] = m
        print(f"    {name:>32} {m['median_maxdd_pct']:>8.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
              f"{m['median_return_pct']:>8.1f}% {m['median_sharpe']:>8.2f}")

    # ---- B) Meta-Umschalter: hilft "nach Vorjahr entscheiden"?
    print(f"\n{'='*96}\nB) Meta-Umschalter: je Jahr die im VORJAHR bessere Variante waehlen\n{'='*96}")
    print("  (Das ist der einfachste denkbare Umschalter. Schlaegt er nicht einmal\n"
          "   die bessere Einzelvariante, ist ein komplexeres Modell auf dieser\n"
          "   Datenmenge erst recht nicht zu rechtfertigen.)\n")
    jahre = sorted(_utc_naive(rep["entry_time"]).dt.year.unique())
    namen = ["ungefiltert", "ribbon-konform (heute)", "A: long immer, short gefiltert"]
    zeilen, oos = [], []
    for y in jahre[1:]:
        vor = {n: varianten[n][_utc_naive(varianten[n]["entry_time"]).dt.year == y - 1]["r"].sum()
               for n in namen}
        wahl = max(vor, key=vor.get)
        r = varianten[wahl][_utc_naive(varianten[wahl]["entry_time"]).dt.year == y]["r"]
        bas = varianten["ribbon-konform (heute)"]
        bas = bas[_utc_naive(bas["entry_time"]).dt.year == y]["r"]
        zeilen.append({"jahr": int(y), "gewaehlt": wahl, "oos_summe_r": float(r.sum()),
                       "ribbon_summe_r": float(bas.sum())})
        oos.append(r)
        print(f"    {y}  Vorjahrssieger: {wahl:<32} -> {r.sum():>+7.1f} R   "
              f"(ribbon-konform: {bas.sum():>+7.1f} R)")
    alle = pd.concat(oos) if oos else pd.Series(dtype=float)
    s_meta = stats(alle)
    s_rib = stats(varianten["ribbon-konform (heute)"][
        _utc_naive(varianten["ribbon-konform (heute)"]["entry_time"]).dt.year >= jahre[1]]["r"])
    print(f"\n    Umschalter gesamt : {s_meta['trades']:>4} Trades, ΣR {s_meta['summe_r']:>+7.1f}, "
          f"Ø R {s_meta['avg_r']:+.3f}, PF {s_meta['profit_factor']:.2f}")
    print(f"    ribbon-konform    : {s_rib['trades']:>4} Trades, ΣR {s_rib['summe_r']:>+7.1f}, "
          f"Ø R {s_rib['avg_r']:+.3f}, PF {s_rib['profit_factor']:.2f}")
    besser = s_meta["summe_r"] > s_rib["summe_r"]
    print(f"    -> Umschalter {'SCHLAEGT' if besser else 'schlaegt NICHT'} die feste Variante")
    result["meta_umschalter"] = {"je_jahr": zeilen, "gesamt": s_meta, "vergleich_ribbon": s_rib,
                                 "schlaegt_feste_variante": bool(besser)}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
