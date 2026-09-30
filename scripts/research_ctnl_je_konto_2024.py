"""CTNL mit Ribbon-Gate: Backtest je KONTO, 2024 bis heute (2026-09-30)

Nutzerfrage nach dem Rollout. Die Beine sind identisch, die Konten nicht --
jedes faehrt eine andere Kapitalscheibe, und daraus folgen andere
Drawdown- und Renditezahlen aus DERSELBEN Trade-Liste.

Risiko je Trade (Kapitalscheibe x Bein-Risiko, aus den Bridge-Configs
gelesen, nicht gesetzt):

  Funded ttp        cont 0,0833 %   rev 0,0250 %   (cw 1/6,  Deckel 1,0 %)
  Funded iqmarkets  cont 0,1667 %   rev 0,0500 %   (cw 1/3,  Deckel 1,0 %)
  FK                cont 0,1263 %   rev 0,0379 %   (cw 0,2525)
  EK                cont 0,0625 %   rev 0,0188 %   (cw 1/8)

WARUM DIE EK-ZAHLEN EINE FUSSNOTE BRAUCHEN
Auf EK greift die Mindestlot-Anhebung: bei ~2.900 EUR Equity riskiert das
kleinste handelbare XAUUSD-Lot rund 25 EUR, waehrend das Ziel bei 0,55 EUR
liegt -- Faktor 46 (Befund 10). Die nominale Rechnung unten beschreibt
EK deshalb NICHT; sie wird zusaetzlich mit dem real erzwungenen Risiko
gerechnet und beides ausgewiesen.

Grundlage ist die gesperrte Config plus Ribbon-Gate -- also genau das, was
seit 2026-09-30 live ist. Kosten 2,01 bps (TTP, der teuerste der vier),
Lag 1, R-Detektor 0,50R.
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

from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h4  # noqa: E402
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS  # noqa: E402
from gold_smc_htf_ltf.ribbon_gate import ribbon_direction  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import leg_trades, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import stats  # noqa: E402

START_JUNG = pd.Timestamp("2024-01-01")

# (Konto, Risiko cont, Risiko rev, Equity-Referenz, harte DD-Grenze?)
KONTEN = [
    ("Funded ttp (Demo)",      0.000833, 0.000250, 100_000, "6 % (TTP)"),
    ("Funded iqmarkets (echt)", 0.001667, 0.000500, 100_000, "6 % (IQ)"),
    ("FK Instant Funding",      0.001263, 0.000379, 100_000, "Trailing"),
    ("EK (nominal)",            0.000625, 0.000188,   2_900, "keine"),
]


def mc(daily: pd.Series, equity: float) -> dict:
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 150:
        return {}
    m = run_monte_carlo(daily, initial_equity=equity, block_size=20, n_sims=2000, seed=42)
    s = m["summary"] if isinstance(m, dict) and "summary" in m else m
    dd = s["max_drawdown_pct"]
    return {"median_maxdd_pct": float(np.median(dd)),
            "p5_maxdd_pct": float(np.percentile(dd, 5)),
            "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
            "median_return_pct": float(np.median(s["total_return_pct"])),
            "median_sharpe": float(np.median(s["sharpe"]))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_je_konto_2024.json")
    args = ap.parse_args()

    bars = load_bars("2022-01-01", args.end)   # Vorlauf fuer Signale + Ribbon
    rib = ribbon_direction(fetch_gold_h4("2022-01-01", args.end),
                           fetch_gold_d1("2022-01-01", args.end))
    r_idx = pd.to_datetime(rib.index)
    rib.index = r_idx.tz_convert(None) if r_idx.tz is not None else r_idx

    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    kw = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    je_bein: dict[str, pd.DataFrame] = {}
    print("Trade-Listen (gesperrte Config + Ribbon-Gate, 2024 bis heute):")
    for leg in ("ctnl_reversal", "ctnl_continuation"):
        rep = to_live(leg_trades(bars, leg, tp_r=tp[leg], sig_kwargs=kw[leg]), bar_src[leg])
        t = _utc_naive(rep["entry_time"])
        rep = rep.assign(rib=rib.reindex(t, method="ffill").to_numpy())
        roh = rep[t >= START_JUNG]
        gate = roh[((roh["direction"] == 1) & (roh["rib"] > 0)) |
                   ((roh["direction"] == -1) & (roh["rib"] < 0))]
        je_bein[leg] = gate
        s_roh, s_gate = stats(roh["r"]), stats(gate["r"])
        print(f"  {leg:20} ungefiltert {s_roh['trades']:>4} Trades Ø R {s_roh['avg_r']:+.3f} PF {s_roh['profit_factor']:.2f}"
              f"  ->  mit Gate {s_gate['trades']:>4} Ø R {s_gate['avg_r']:+.3f} PF {s_gate['profit_factor']:.2f}")

    result: dict = {"stand": args.end, "beine": {}, "konten": {}}
    for leg, d in je_bein.items():
        result["beine"][leg] = stats(d["r"])

    print(f"\n{'='*104}")
    print(f"{'Konto':24} {'Trades':>7} {'ΣR':>8} | {'Median MaxDD':>13} {'P5':>8} {'P(>6%)':>8} "
          f"{'Median Return':>14} {'Sharpe':>7}")
    print("="*104)
    for name, r_cont, r_rev, equity, grenze in KONTEN:
        teile = []
        for leg, risk in (("ctnl_continuation", r_cont), ("ctnl_reversal", r_rev)):
            d = je_bein[leg]
            if d.empty:
                continue
            teile.append((d.set_index(_utc_naive(d["entry_time"]))["r"] * risk).resample("D").sum())
        if not teile:
            continue
        daily = pd.concat(teile, axis=1).fillna(0).sum(axis=1)
        m = mc(daily, equity)
        n = sum(len(je_bein[l]) for l in je_bein)
        sr = sum(je_bein[l]["r"].sum() for l in je_bein)
        result["konten"][name] = {"risiko_cont": r_cont, "risiko_rev": r_rev,
                                  "equity_referenz": equity, "dd_grenze": grenze, **m}
        if m:
            print(f"{name:24} {n:>7} {sr:>+8.1f} | {m['median_maxdd_pct']:>12.2f}% {m['p5_maxdd_pct']:>7.2f}% "
                  f"{m['P_maxdd_ueber_6pct']:>7.1%} {m['median_return_pct']:>13.1f}% {m['median_sharpe']:>7.2f}"
                  f"   (DD-Grenze {grenze})")
        else:
            print(f"{name:24} {n:>7} {sr:>+8.1f} | zu wenige Handelstage fuer Monte Carlo")

    # EK real: Mindestlot-Anhebung, siehe Modul-Docstring
    print(f"\n  EK REAL (Mindestlot-Anhebung, Befund 10): das kleinste XAUUSD-Lot riskiert")
    print(f"  bei ~2.900 EUR Equity rund 25 EUR = 0,86 %/Trade statt der nominalen 0,019 %.")
    d = je_bein["ctnl_reversal"]
    if not d.empty:
        daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * 0.0086).resample("D").sum()
        m = mc(daily, 2_900)
        if m:
            result["konten"]["EK (real, Mindestlot)"] = {"risiko_rev": 0.0086, **m}
            print(f"  -> nur ctnl_reversal bei 0,86 %/Trade: Median MaxDD {m['median_maxdd_pct']:.2f}%, "
                  f"P(>6 %) {m['P_maxdd_ueber_6pct']:.1%}, Median Return {m['median_return_pct']:.1f}%, "
                  f"Sharpe {m['median_sharpe']:.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
