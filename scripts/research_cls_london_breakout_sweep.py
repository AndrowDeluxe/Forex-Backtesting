"""Parameter-Sweep für strategy/cls_london_breakout.py - Stellschrauben
Entry (confirm_bars), SL (atr_mult), TP (tp_r_mult) und BE (be_trigger_r).
Der Baseline-Befund (2026-08-07, confirm_bars=2/atr_mult=1.0/tp_r_mult=2.0/
be_trigger_r=1.0) war klar negativ (PF 0.36, 0/11 Jahre positiv) - dieser
Sweep prüft, ob eine andere Kombination innerhalb desselben Grundgerüsts
eine reale Verbesserung zeigt oder ob das Grundgerüst selbst nicht trägt.
Reportet IS UND OOS für jede Kombination (nicht nur Full-Period) - eine
Kombination, die nur pooled gut aussieht aber IS/OOS auseinanderläuft, ist
kein Fund, sondern Overfitting an genau diesen einen Sweep-Lauf (gleiches
Muster wie schon mehrfach in diesem Projekt beobachtet)."""

import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from strategy.cls_london_breakout import fetch_eurusd_m15_berlin, simulate_london_cls_breakout
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
MIN_TRADES_FULL = 100  # unter dieser Schwelle: Kombination gar nicht erst reporten (zu duenn)

CONFIRM_BARS = [1, 2, 3]
ATR_MULT = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_R_MULT = [1.5, 2.0, 3.0]
BE_TRIGGER_R = [None, 1.0, 1.5]


def main():
    print(f"Fetching EURUSD M15 (Berlin tz) {START} -> {END} ...")
    df = fetch_eurusd_m15_berlin(START, END)
    print(f"{len(df)} bars fetched.\n")

    combos = list(product(CONFIRM_BARS, ATR_MULT, TP_R_MULT, BE_TRIGGER_R))
    print(f"Running {len(combos)} combinations ...")

    rows = []
    for confirm_bars, atr_mult, tp_r_mult, be_trigger_r in combos:
        trades = simulate_london_cls_breakout(
            df,
            atr_mult=atr_mult,
            tp_r_mult=tp_r_mult,
            be_trigger_r=be_trigger_r,
            confirm_bars=confirm_bars,
        )
        full = trade_stats(trades)
        if full["n_trades"] < MIN_TRADES_FULL:
            continue
        is_trades = trades[trades["entry_time"] < SPLIT]
        oos_trades = trades[trades["entry_time"] >= SPLIT]
        is_s = trade_stats(is_trades)
        oos_s = trade_stats(oos_trades)
        rows.append(
            {
                "confirm_bars": confirm_bars,
                "atr_mult": atr_mult,
                "tp_r_mult": tp_r_mult,
                "be_trigger_r": be_trigger_r,
                "n_trades": full["n_trades"],
                "pf_full": full["profit_factor"],
                "wr_full": full["win_rate"],
                "pf_is": is_s["profit_factor"],
                "pf_oos": oos_s["profit_factor"],
                "n_is": is_s["n_trades"],
                "n_oos": oos_s["n_trades"],
            }
        )

    results = pd.DataFrame(rows)
    results["pf_min_is_oos"] = results[["pf_is", "pf_oos"]].min(axis=1)

    print(f"\n{len(results)}/{len(combos)} combinations had >= {MIN_TRADES_FULL} trades.\n")

    print("=== Top 15 by pooled full-period profit factor ===")
    print(results.sort_values("pf_full", ascending=False).head(15).to_string(index=False))

    print("\n=== Top 15 by MIN(IS, OOS) profit factor - robust across both halves, not just pooled ===")
    print(results.sort_values("pf_min_is_oos", ascending=False).head(15).to_string(index=False))

    print("\n=== How many combinations clear PF > 1.0 pooled? ===")
    print(f"{(results['pf_full'] > 1.0).sum()} / {len(results)}")
    print("=== How many clear PF > 1.0 on BOTH IS and OOS? ===")
    print(f"{(results['pf_min_is_oos'] > 1.0).sum()} / {len(results)}")


if __name__ == "__main__":
    main()
