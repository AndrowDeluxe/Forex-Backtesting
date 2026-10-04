"""trend_pullback + gold_silver: SL-Multiplikator (Gitter + Walk-Forward) und
EK-Ausfuehrungspfad gegen FK-Pfad. Nutzerfrage 2026-10-04 "Kann man an der
SL-Setzung nochmal etwas optimieren?" + Bridge-Vergleich.

Baut auf research_trend_gs_ausfuehrung.py auf (gleiche Live-Semantik:
Intrabar-SL auf M15, Scan-Exit, Gates). Zwei Fragen:
  1. EK handelt beide Beine mit Broker-TP 2R, ohne R-Detektor, Signal bis 4 h
     alt (core/bracket_executor.py) -- FK mit Scan-Exit, R-Detektor, 150 Min.
     Was kostet der EK-Pfad?
  2. Stop-Multiplikator 1,5-4,0 ATR (heute 2,0), Anker-Walk-Forward ab 2021,
     Wahl nach Σ R der Vorjahre.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_trend_gs_ausfuehrung as A  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MULTS = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)


def main() -> None:
    import mt5_gold_silver_divergenz.pipeline as GS
    import mt5_trend_pullback.pipeline as TP

    bars = A.m15_bars()
    base = A.engine_trades()
    gs = base[base["leg"] == "gold_silver"]
    print("EK-Pfad gold_silver (Broker-TP 2R, ohne R-Detektor):")
    for lag in (0, 60, 120, 180, 240):
        print(f"  Lag {lag:3d}", A.stats(A.replay(gs, bars, lag_min=lag, mode="broker", tp_r=2.0, gate_r=9.0, max_age=300)))
    print("FK-Pfad gold_silver (Scan-Exit, Lag 20):", A.stats(A.replay(gs, bars, lag_min=20, mode="scan")))

    res = {}
    for m in MULTS:
        TP.ATR_STOP_MULT = GS.ATR_STOP_MULT = m
        t = A.engine_trades()
        res[m] = {}
        for leg in ("trend_pullback", "gold_silver"):
            r = A.replay(t[t["leg"] == leg], bars, lag_min=20, mode="scan")
            res[m][leg] = r[r["status"] == "gefuellt"].assign(y=lambda d: d["entry_time"].dt.year)
    for leg in ("trend_pullback", "gold_silver"):
        print(f"\n{leg}: Ø R je Jahr x Stop-Multiplikator")
        print(pd.DataFrame({m: res[m][leg].groupby("y")["r"].mean() for m in MULTS}).round(2).to_string())
        tot = 0.0
        for y in range(2021, 2027):
            is_sum = {m: res[m][leg].query("y < @y")["r"].sum() for m in MULTS}
            m = max(is_sum, key=is_sum.get)
            d = res[m][leg].query("y == @y")["r"].sum() - res[2.0][leg].query("y == @y")["r"].sum()
            tot += d
            print(f"  WF {y}: gewaehlt {m} ATR, Δ Σ R gegen 2,0 ATR {d:+.1f}")
        print(f"  WF Summe Δ Σ R: {tot:+.1f}")


if __name__ == "__main__":
    main()
