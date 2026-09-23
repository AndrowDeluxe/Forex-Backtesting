"""CTNL: Richtung je Bein + der Struktur-gegen-Regime-Test (2026-09-23)

Zwei Nutzeraufträge nach Befund 11:

  (1) `ctnl_continuation` ebenfalls nach long/short aufteilen und wie das
      Reversal-Bein durch Walk-Forward und Monte Carlo schicken.

  (2) DER ENTSCHEIDENDE TEST: verdient die Short-Seite in den Jahren, in denen
      Gold FAELLT? Befund 11 zeigte short ueber die Gesamthistorie mit
      ΣR -122,3 -- aber Gold ist von ~1.150 (2016) auf ~4.400 (2026)
      gestiegen. "Long funktioniert, Short nicht" ist auf einem einseitig
      steigenden Markt nahe an einer Tautologie.

      Die Frage, die das trennt: haengt die Short-Performance an der
      JAEHRLICHEN GOLD-RICHTUNG?
        - Verdienen Shorts in fallenden Jahren und verlieren nur in
          steigenden -> die Asymmetrie ist ein REGIME-Effekt. Long-only waere
          dann eine Trendwette, die man bei einer Trendwende zurueckdrehen
          muss.
        - Verlieren Shorts AUCH in fallenden Jahren -> die Asymmetrie ist
          STRUKTURELL (die Kaskade taugt auf der Short-Seite schlicht nicht).
          Dann waere Long-only eine echte Verbesserung.

      Die Stichprobe ist klein (10 Jahre, davon wenige fallende) -- das
      Ergebnis wird die Frage nicht endgueltig klaeren, aber es sagt, in
      welche Richtung die Datenlage zeigt. Das wird unten ausdruecklich
      ausgewiesen statt weggerundet.
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
    attach_feature,
    leg_trades,
    regime_feature,
    surface,
    to_live,
)

RISK_PCT = {"ctnl_reversal": 0.0015, "ctnl_continuation": 0.005}  # FK-Split, live_signal.py


def mc_row(d: pd.DataFrame, risk_pct: float) -> dict:
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * risk_pct).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 250:
        return {}
    mc = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
    dd = s["max_drawdown_pct"]
    return {"median_maxdd_pct": float(np.median(dd)),
            "p5_maxdd_pct": float(np.percentile(dd, 5)),
            "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
            "median_return_pct": float(np.median(s["total_return_pct"])),
            "median_sharpe": float(np.median(s["sharpe"]))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_direction_regime.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    kwargs = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    base_tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    # Gold-Jahresrichtung aus den H1-Bars (Schluss zu Schluss)
    h1 = bars["h1"]
    gi = _utc_naive(h1.index)
    gclose = pd.Series(h1["close"].to_numpy(), index=gi)
    jahres_close = gclose.resample("YE").last()
    gold_jahr = (jahres_close.pct_change() * 100).dropna()
    gold_jahr.index = gold_jahr.index.year

    result: dict = {"beine": {}, "gold_jahresrendite_pct": {int(k): float(v) for k, v in gold_jahr.items()}}

    for leg in ("ctnl_reversal", "ctnl_continuation"):
        print(f"\n{'='*84}\n{leg}\n{'='*84}")
        tr = leg_trades(bars, leg, tp_r=base_tp[leg], sig_kwargs=kwargs[leg])
        rep = to_live(tr, bar_src[leg])
        rep = attach_feature(rep, regime_feature(bar_src[leg])).dropna(subset=["feat"])
        thr = rep["feat"].quantile(0.50)

        varianten = {
            "beide (Baseline)": rep,
            "nur long": rep[rep["direction"] == 1],
            "nur short": rep[rep["direction"] == -1],
            "long + Regime": rep[(rep["direction"] == 1) & (rep["feat"] <= thr)],
        }
        res = {"regime_schwelle_abs": float(thr)}
        res["flaeche"] = surface(varianten, f"{leg}: Richtung")
        res["walkforward"] = anchored_walk_forward(varianten, "beide (Baseline)", f"{leg}: Richtung")

        print(f"\n  Monte Carlo ({RISK_PCT[leg]:.2%}/Trade, 2000 Pfade, Block 20):")
        print(f"    {'Variante':>18} {'MedMaxDD':>10} {'P5 DD':>9} {'P(>6%)':>8} {'MedReturn':>11} {'Sharpe':>8}")
        res["monte_carlo"] = {}
        for name, d in varianten.items():
            m = mc_row(d, RISK_PCT[leg])
            if not m:
                continue
            res["monte_carlo"][name] = m
            print(f"    {name:>18} {m['median_maxdd_pct']:>9.2f}% {m['p5_maxdd_pct']:>8.2f}% "
                  f"{m['P_maxdd_ueber_6pct']:>7.1%} {m['median_return_pct']:>10.1f}% {m['median_sharpe']:>8.2f}")

        # ---- Der Struktur-gegen-Regime-Test
        print(f"\n  STRUKTUR ODER REGIME? Short-Ergebnis gegen die Gold-Jahresrichtung")
        print(f"    {'Jahr':>6} {'Gold %':>8} {'short n':>8} {'short ØR':>9} {'short ΣR':>9} "
              f"{'long ØR':>8} {'long ΣR':>9}")
        zeilen = []
        for jahr in sorted(rep["jahr"].unique()):
            g = gold_jahr.get(jahr)
            sh = rep[(rep["jahr"] == jahr) & (rep["direction"] == -1)]["r"]
            lo = rep[(rep["jahr"] == jahr) & (rep["direction"] == 1)]["r"]
            if g is None or len(sh) == 0:
                continue
            zeilen.append({"jahr": int(jahr), "gold_pct": float(g),
                           "short_n": int(len(sh)), "short_avg_r": float(sh.mean()),
                           "short_sum_r": float(sh.sum()),
                           "long_avg_r": float(lo.mean()) if len(lo) else float("nan"),
                           "long_sum_r": float(lo.sum())})
            print(f"    {jahr:>6} {g:>+8.1f} {len(sh):>8} {sh.mean():>+9.3f} {sh.sum():>+9.1f} "
                  f"{(lo.mean() if len(lo) else float('nan')):>+8.3f} {lo.sum():>+9.1f}")
        res["struktur_vs_regime"] = zeilen

        if len(zeilen) >= 4:
            df = pd.DataFrame(zeilen)
            gefallen = df[df["gold_pct"] < 0]
            gestiegen = df[df["gold_pct"] >= 0]
            korr = df["gold_pct"].corr(df["short_avg_r"])
            print(f"\n    Jahre mit fallendem Gold : {len(gefallen)}"
                  + (f" -> short Ø R {gefallen['short_avg_r'].mean():+.3f}, ΣR {gefallen['short_sum_r'].sum():+.1f}" if len(gefallen) else " -> KEINE im Sample"))
            print(f"    Jahre mit steigendem Gold: {len(gestiegen)}"
                  + (f" -> short Ø R {gestiegen['short_avg_r'].mean():+.3f}, ΣR {gestiegen['short_sum_r'].sum():+.1f}" if len(gestiegen) else ""))
            print(f"    Korrelation Gold-Jahresrendite <-> short Ø R: {korr:+.2f} "
                  f"(negativ = Shorts verdienen, wenn Gold faellt = REGIME-Effekt)")
            res["auswertung"] = {
                "n_jahre_fallend": int(len(gefallen)),
                "n_jahre_steigend": int(len(gestiegen)),
                "short_avg_r_fallende_jahre": float(gefallen["short_avg_r"].mean()) if len(gefallen) else None,
                "short_avg_r_steigende_jahre": float(gestiegen["short_avg_r"].mean()) if len(gestiegen) else None,
                "korrelation_gold_vs_short": float(korr),
            }
        result["beine"][leg] = res

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
