"""Traegt das Ribbon-Richtungsgate auch auf den anderen GOLD-Beinen? (2026-09-30)

Nutzerauftrag: "implementiere die gesamte Logik auf allen Beinen".

WARUM DAS NICHT WOERTLICH GEHT
Der MTF-EMA-Ribbon besteht aus H4-, D1- und W1-EMAs auf XAUUSD. Auf
cls_practical (EURUSD), ou_modell (US-Einzelaktien), orb_* (Indizes) oder
btc_ema_cross angewandt hiesse er: der GOLD-Trend entscheidet, ob eine
Apple-Aktie gekauft werden darf. Das ist keine Uebertragung, sondern ein
Kategorienfehler.

Die Uebertragung per Analogie ist in dieser Untersuchung ausserdem schon
zweimal widerlegt worden: das Strukturziel (Befund 16c, SigmaR +141,8 statt
+330,6) und die Signal-Parameter (Befund 9b, IS-Sieger in 8/8 Jahren, OOS
verloren). Deshalb hier: MESSEN, nicht uebertragen.

GEPRUEFT WERDEN die Beine, die tatsaechlich Gold handeln:
  gold_asb        XAUUSD
  trend_pullback  XAUUSD/XAGUSD/XPTUSD (die Nicht-Gold-Maerkte bleiben aussen
                  vor -- fuer CHFJPY/USDJPY ist der Gold-Ribbon genauso
                  sinnlos wie fuer EURUSD)

Fuer jedes Bein dieselbe Disziplin wie bei CTNL: Parameterflaeche,
Anker-Walk-Forward (Parameter je Jahr auf allen Trades DAVOR gewaehlt) und
Monte Carlo. Ein Bein wird nur dann zum Eintrag in RIBBON_GATED_LEGS
vorgeschlagen, wenn die Prozedur die ungefilterte Baseline out-of-sample
schlaegt.
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

import challenge_portfolio.paper_bot as pb  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h4  # noqa: E402
from gold_smc_htf_ltf.ribbon_gate import ribbon_direction  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _utc_naive  # noqa: E402
from research_ctnl_optimization import anchored_walk_forward, surface  # noqa: E402
from research_ctnl_ribbon_both_legs import stats  # noqa: E402

JUNG = pd.Timestamp("2024-01-01")
# Risiko je Trade laut challenge_portfolio/paper_bot.py::LEG_RISK_PCT
RISK = {"gold_asb": 0.02, "trend_pullback": 0.005}
GOLD_MAERKTE = {"XAUUSD", "XAGUSD", "XPTUSD"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ribbon_andere_beine.json")
    args = ap.parse_args()

    ende = pd.Timestamp(args.end)
    h4, d1 = fetch_gold_h4(args.start, args.end), fetch_gold_d1(args.start, args.end)
    rib = ribbon_direction(h4, d1)
    r_idx = pd.to_datetime(rib.index)
    rib.index = r_idx.tz_convert(None) if r_idx.tz is not None else r_idx
    print(f"Ribbon: {len(rib):,} H4-Punkte, "
          f"{(rib == 1).mean():.0%} auf / {(rib == -1).mean():.0%} ab / {(rib == 0).mean():.0%} neutral")

    result: dict = {}

    for leg, scan in (("gold_asb", pb._scan_gold_asb), ("trend_pullback", pb._scan_trend_pullback)):
        print(f"\n{'='*90}\n{leg}\n{'='*90}")
        try:
            tr = scan(ende, force_refresh=False, source="live")
        except Exception as e:
            print(f"  Scan fehlgeschlagen: {type(e).__name__}: {e}")
            continue
        if tr is None or tr.empty:
            print("  keine Trades")
            continue

        if leg == "trend_pullback" and "market" in tr.columns:
            vorher = len(tr)
            tr = tr[tr["market"].isin(GOLD_MAERKTE)]
            print(f"  {len(tr)} von {vorher} Trades auf Gold-Maerkten "
                  f"(Rest bleibt aussen vor -- Gold-Ribbon dort sinnlos)")
        if tr.empty:
            continue

        t = _utc_naive(tr["entry_time"])
        d = tr["direction"].map(lambda x: 1 if x in (1, "long") else -1).to_numpy()
        stand = rib.reindex(t, method="ffill").to_numpy()
        tr = tr.assign(jahr=t.dt.year, r=tr["r_multiple"], rib=stand, d=d)
        tr = tr.dropna(subset=["rib", "r"])
        print(f"  {len(tr)} Trades mit Ribbon-Wert, "
              f"{tr['jahr'].min()}-{tr['jahr'].max()}")
        if len(tr) < 60:
            print("  -> zu wenige Trades fuer eine belastbare Aussage, uebersprungen")
            continue

        varianten = {
            "Baseline": tr,
            "ribbon-konform": tr[((tr["d"] == 1) & (tr["rib"] > 0)) | ((tr["d"] == -1) & (tr["rib"] < 0))],
            "ribbon long-only": tr[(tr["d"] == 1) & (tr["rib"] > 0)],
        }
        res = {"flaeche": surface(varianten, f"{leg}: Ribbon-Richtung")}

        print(f"\n  Nur 2024-2026:")
        print(f"    {'Variante':>18} {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
        res["jung"] = {}
        for name, x in varianten.items():
            j = stats(x[_utc_naive(x["entry_time"]) >= JUNG]["r"])
            res["jung"][name] = j
            print(f"    {name:>18} {j['trades']:>5} {j['avg_r']:>+8.3f} {j['summe_r']:>+8.1f} {j['profit_factor']:>6.2f}")

        res["walkforward"] = anchored_walk_forward(varianten, "Baseline", f"{leg}: Ribbon-Richtung")

        print(f"\n  Monte Carlo ({RISK[leg]:.2%}/Trade):")
        print(f"    {'Variante':>18} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
        res["monte_carlo"] = {}
        for name, x in varianten.items():
            daily = (x.set_index(_utc_naive(x["entry_time"]))["r"] * RISK[leg]).resample("D").sum()
            daily = daily[daily.index.dayofweek < 5]
            if len(daily) < 250:
                continue
            mc = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
            s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
            dd = s["max_drawdown_pct"]
            res["monte_carlo"][name] = {
                "median_maxdd_pct": float(np.median(dd)),
                "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
                "median_return_pct": float(np.median(s["total_return_pct"])),
                "median_sharpe": float(np.median(s["sharpe"]))}
            v = res["monte_carlo"][name]
            print(f"    {name:>18} {v['median_maxdd_pct']:>8.2f}% {v['P_maxdd_ueber_6pct']:>7.1%} "
                  f"{v['median_return_pct']:>8.1f}% {v['median_sharpe']:>8.2f}")

        wf = res["walkforward"]
        empfehlung = wf["oos"]["summe_r"] > wf["baseline"]["summe_r"]
        res["empfehlung_gaten"] = bool(empfehlung)
        print(f"\n  URTEIL: Ribbon-Gate fuer {leg} "
              f"{'EMPFOHLEN' if empfehlung else 'NICHT empfohlen'} "
              f"(OOS ΣR {wf['oos']['summe_r']:+.1f} gegen {wf['baseline']['summe_r']:+.1f})")
        result[leg] = res

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
