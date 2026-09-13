"""ATR-Boden ueber mehrere Timeframes und ADR-Ziel ueber mehrere Perioden --
Gegenprobe zum festen Pip-Boden (Nutzerauftrag 2026-09-10: "teste das ganze
nochmal kurz mit verschiedenen ATR Werten in verschiedenen Timeframes und eben
auch als Ziel mit verschiedenen ADR Parametern").

WORUM ES GEHT: die SL-Studie hat gezeigt, dass ein FESTER Pip-Boden von 5 Pips
die Strategie unter TTP-Kosten rettet (PF 1,11 -> 1,52), waehrend der bestehende
RELATIVE Boden `min_sl_atr_mult x ATR(M5)` versagt. Der naheliegende Verdacht:
nicht "relativ" war das Problem, sondern "ATR auf M5". Der M5-ATR liegt im
Median bei nur 3,18 Pips und schwankt stark von Minute zu Minute -- genau
deshalb ging am 2026-09-09 ein 3,6-Pip-Stop durch. Auf hoeheren Timeframes ist
dieselbe Groesse deutlich ruhiger (M15 5,87 / M30 8,58 / H1 12,33 Pips Median).

Ein ATR-Boden auf H1 waere, anders als der feste Pip-Boden, REGIME-ADAPTIV: er
wandert in volatilen Phasen mit, statt stur bei 5 Pips zu stehen. Wenn er
dieselbe Wirkung erzielt, ist er dem festen Boden vorzuziehen. Wenn nicht,
gewinnt die einfachere Loesung.

Die Multiplikatoren sind je Timeframe SO GEWAEHLT, dass sie vergleichbare
Boeden von ~3-9 Pips erzeugen -- sonst vergliche man Timeframe-Effekt und
Bodenhoehe durcheinander.

TEIL 2 entkoppelt ausserdem erstmals `adr_period` (Tagesrange-Ziel) vom
ATR des SL-Bodens -- bisher trieb EIN Parameter beide Groessen.

Alle Laeufe unter den gemessenen TTP-Kosten (2,05 Pips Round-Trip).

Aufruf:
    python scripts/research_cls_practical_atr_adr_grid.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    RISK_PCT,
    evaluate,
    pips_to_bps,
)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 300)

# (Timeframe-Regel, Anzeigename, Multiplikatoren) -- Multiplikatoren so
# gewaehlt, dass alle Timeframes Boeden im selben ~3-9-Pip-Band erzeugen.
ATR_GRID = [
    (None,    "M5",  [1.0, 1.5, 2.0, 2.5]),
    ("15min", "M15", [0.5, 0.75, 1.0, 1.5]),
    ("30min", "M30", [0.4, 0.6, 0.8, 1.0]),
    ("1h",    "H1",  [0.25, 0.4, 0.5, 0.75]),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    args = ap.parse_args()

    print(f"Lade Daten {args.start}..{args.end} ...")
    e = fetch_eurusd_entry_tf_berlin("M5", args.start, args.end)
    o = {p: fetch_major_m15_berlin(p, args.start, args.end) for p in OTHER_MAJORS}
    b = fetch_rate_instrument_m5_berlin("BUND", args.start, args.end)
    u = fetch_rate_instrument_m5_berlin("USTBOND", args.start, args.end)
    price = float(e["close"].mean())
    print(f"  {len(e):,} M5-Baren\n")

    def sim(**kw):
        return simulate_cls_practical(
            e, o, b, u, risk_pct=RISK_PCT,
            spread_bps=pips_to_bps(COSTS_PIPS["TTP"], price), slippage_bps=0.0, **kw,
        )

    def slim(row, extra=None):
        keep = ["Variante", "Setup", "Trades", "Treffer%", "PF", "Ø R", "Ø R (IS)",
                "Ø R (OOS)", "PnL $", "MaxDD %", "SL med (Pips)", "SL p10", "Hebel p90"]
        out = {k: row.get(k) for k in keep}
        if extra:
            out.update(extra)
        return out

    # ---------------------------------------------------- Teil 1: ATR-Boden
    print("=" * 175)
    print("TEIL 1 -- ATR-BODEN ueber Timeframes (Modus 'drop'). Referenzen unten zum Vergleich.")
    print("=" * 175)
    rows = []
    for rule, name, mults in ATR_GRID:
        for m in mults:
            kw = {"min_sl_atr_mult": m}
            if rule is not None:
                kw["atr_timeframe"] = rule
            t = sim(**kw)
            rows.append(slim(evaluate(t, f"mult={m:g}", f"ATR {name}")))
    for label, kw in (("Referenz: kein Boden", {}),
                      ("Referenz: Pip-Boden 5", {"min_sl_pips": 5}),
                      ("Referenz: Pip-Boden 6", {"min_sl_pips": 6})):
        rows.append(slim(evaluate(sim(**kw), "-", label)))
    df1 = pd.DataFrame(rows)
    print(df1.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ATR-Periode auf dem besten Timeframe variieren
    atr_only = df1[df1["Variante"].str.startswith("ATR")]
    best = atr_only.loc[atr_only["Ø R (OOS)"].idxmax()]
    best_tf = best["Variante"].split()[1]
    rule_of = {"M5": None, "M15": "15min", "M30": "30min", "H1": "1h"}
    best_mult = float(best["Setup"].split("=")[1])
    print(f"\n  Bester ATR-Timeframe nach OOS: {best['Variante']} {best['Setup']} "
          f"(Ø R OOS {best['Ø R (OOS)']:.2f})")
    print("\n" + "=" * 175)
    print(f"TEIL 1b -- ATR-PERIODE auf {best_tf} variieren (mult={best_mult:g} fest)")
    print("=" * 175)
    rows_b = []
    for n in (7, 10, 14, 21, 28):
        kw = {"min_sl_atr_mult": best_mult, "atr_period": n}
        if rule_of[best_tf] is not None:
            kw["atr_timeframe"] = rule_of[best_tf]
        rows_b.append(slim(evaluate(sim(**kw), f"atr_period={n}", f"ATR {best_tf}")))
    print(pd.DataFrame(rows_b).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ------------------------------------------------- Teil 2: ADR-Ziel
    print("\n" + "=" * 175)
    print("TEIL 2 -- ADR-ZIEL: Periode x Multiplikator, bei festem Pip-Boden 5 "
          "(adr_period ist jetzt vom ATR entkoppelt)")
    print("=" * 175)
    rows2 = []
    for ap_ in (5, 10, 14, 20, 30):
        for am in (0.35, 0.50, 0.75):
            t = sim(min_sl_pips=5, adr_period=ap_, adr_mult=am, atr_period=14)
            rows2.append(slim(evaluate(t, f"adr_mult={am:g}", f"adr_period={ap_}")))
    df2 = pd.DataFrame(rows2)
    print(df2.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    print("\n  Hinweis: atr_period=14 hier fest gesetzt, damit adr_period NUR das Ziel "
          "veraendert und nicht gleichzeitig den SL-Boden (bisherige Kopplung).")

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "atr_timeframe_grid.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df1.to_csv(out, index=False)
    pd.DataFrame(rows_b).to_csv(out.with_name("atr_period_grid.csv"), index=False)
    df2.to_csv(out.with_name("adr_target_grid.csv"), index=False)
    print(f"\nGespeichert: {out} (+ atr_period_grid, adr_target_grid)")


if __name__ == "__main__":
    main()
