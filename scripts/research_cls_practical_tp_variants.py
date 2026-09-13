"""TP-Varianten in Kombination mit dem Pip-Boden, unter echten Broker-Kosten
(Nutzerauftrag 2026-09-10: "backteste nochmal zu dem Pip Floor einen festen TP
von 2R und andere Varianten").

VORGESCHICHTE: scripts/research_cls_practical_sl_optimization.py hat gezeigt,
dass ein absoluter Pip-Boden auf den Stop-Abstand (`min_sl_pips`, Modus "drop")
die Strategie unter den gemessenen TTP-Kosten von 2,05 Pips wieder tragfaehig
macht (PF 1,11 -> 1,52 bei min_sl_pips=5), waehrend Stop-Aufweiten ("widen")
und ein volatilitaetsgemittelter fester Stop beide scheitern.

Offene Frage danach: das TP-Ziel war in all diesen Laeufen unveraendert
`adr_mult x ADR(14)` (tp_mode="adr", adr_mult=0.35). Weil der Pip-Boden die
Verteilung der Stop-Abstaende verschiebt, verschiebt er auch das effektive
R:R -- das TP-Ziel ist bei "adr" naemlich UNABHAENGIG vom Stop-Abstand, ein
enger Stop erzeugt also nominal riesige R-Vielfache. Ob ein an den Stop
GEKOPPELTES Ziel (tp_mode="fixed_r") in dieser neuen Verteilung besser
abschneidet, ist damit offen.

GETESTET (jeweils x min_sl_pips in {4, 5, 6}, plus Baseline ohne Boden):
  1. tp_mode="fixed_r", rr_fixed in {1.0, 1.5, 2.0, 2.5, 3.0, 4.0}
     -> Ziel als festes Vielfaches des eigenen Stops. rr=2.0 ist der vom
        Nutzer explizit angefragte Fall.
  2. tp_mode="adr", adr_mult in {0.25, 0.35, 0.50, 0.75}
     -> das bestehende Tagesrange-Ziel, enger und weiter gefasst.
  3. be_trigger_r in {1.0, 1.5} auf den jeweils besten Konfigurationen
     -> Break-even-Nachziehen als dritte Exit-Variante.

BEWERTUNG wie in der SL-Studie: primaer unter TTP-Kosten (2,05 Pips, der harte
Fall), immer mit In-Sample/Out-of-Sample-Trennung ab 2022-06-01 und mit dem
erzeugten Hebel, und Gegenprobe der Besten unter IQ-Kosten (1,30 Pips).

Aufruf:
    python scripts/research_cls_practical_tp_variants.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

# Kennzahlen-/Umrechnungslogik NICHT duplizieren -- dieselbe Bewertung wie in
# der SL-Studie, damit die Tabellen direkt vergleichbar sind.
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    RISK_PCT,
    SPLIT,
    evaluate,
    pips_to_bps,
)

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 300)

PIP_FLOORS = [None, 4, 5, 6]


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

    def sim(cost_pips: float, **kw) -> pd.DataFrame:
        return simulate_cls_practical(
            e, o, b, u, risk_pct=RISK_PCT,
            spread_bps=pips_to_bps(cost_pips, price), slippage_bps=0.0, **kw,
        )

    def floor_kw(fl):
        return {} if fl is None else {"min_sl_pips": fl}

    def floor_label(fl):
        return "kein Boden" if fl is None else f"Boden {fl}p"

    combos: list[tuple[str, str, dict]] = []
    for fl in PIP_FLOORS:
        combos.append((f"TP adr 0.35 (Ist) | {floor_label(fl)}", "Referenz", floor_kw(fl)))
    for fl in PIP_FLOORS:
        for rr in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
            combos.append((f"TP {rr:g}R fix | {floor_label(fl)}", f"fixed_r={rr:g}",
                           {**floor_kw(fl), "tp_mode": "fixed_r", "rr_fixed": rr}))
    for fl in PIP_FLOORS:
        for am in (0.25, 0.50, 0.75):
            combos.append((f"TP adr {am:g} | {floor_label(fl)}", f"adr_mult={am:g}",
                           {**floor_kw(fl), "adr_mult": am}))

    print("=" * 215)
    print(f"UNTER TTP-KOSTEN ({COSTS_PIPS['TTP']} Pips Round-Trip)")
    print("=" * 215)
    rows = [evaluate(sim(COSTS_PIPS["TTP"], **kw), setup, name) for name, setup, kw in combos]
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # Referenz: Pip-Boden 5 mit dem bestehenden ADR-Ziel (Ergebnis der SL-Studie)
    ref = df[df["Variante"] == "TP adr 0.35 (Ist) | Boden 5p"].iloc[0]
    print(f"\n  Referenz aus der SL-Studie (Boden 5p, TP adr 0.35): "
          f"PF {ref['PF']:.2f} | Ø R {ref['Ø R']:.2f} | OOS {ref['Ø R (OOS)']:.2f} | MaxDD {ref['MaxDD %']:.2f}%")

    better = df[(df["Ø R (OOS)"] > ref["Ø R (OOS)"]) & (df["Ø R (IS)"] > 0) & (df["Trades"] >= 80)]
    better = better.sort_values("Ø R (OOS)", ascending=False)
    print("\n" + "=" * 215)
    print("BESSER ALS DIESE REFERENZ (OOS hoeher, IS positiv, >=80 Trades)")
    print("=" * 215)
    print("  keine" if better.empty else better.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # --- Break-even-Nachziehen auf den aussichtsreichsten Konfigurationen
    top = (better if not better.empty else df.sort_values("Ø R (OOS)", ascending=False)).head(3)
    lookup = {name: kw for name, _, kw in combos}
    print("\n" + "=" * 215)
    print("BREAK-EVEN-NACHZIEHEN (be_trigger_r) AUF DEN AUSSICHTSREICHSTEN KONFIGURATIONEN")
    print("=" * 215)
    be_rows = []
    for name in list(top["Variante"]) + ["TP adr 0.35 (Ist) | Boden 5p", "TP 2R fix | Boden 5p"]:
        kw = lookup.get(name)
        if kw is None:
            continue
        for be in (None, 1.0, 1.5):
            tag = "ohne BE" if be is None else f"BE bei {be:g}R"
            be_rows.append(evaluate(sim(COSTS_PIPS["TTP"], **kw, be_trigger_r=be), tag, name))
    be_df = pd.DataFrame(be_rows).drop_duplicates(subset=["Variante", "Setup"])
    print(be_df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # --- Gegenprobe unter IQ-Kosten
    print("\n" + "=" * 215)
    print(f"GEGENPROBE UNTER IQ-KOSTEN ({COSTS_PIPS['IQ']} Pips)")
    print("=" * 215)
    iq_names = list(dict.fromkeys(
        list(top["Variante"]) + ["TP adr 0.35 (Ist) | Boden 5p", "TP 2R fix | Boden 5p",
                                 "TP adr 0.35 (Ist) | kein Boden"]))
    iq_rows = []
    for name in iq_names:
        kw = lookup.get(name)
        if kw is None:
            continue
        iq_rows.append(evaluate(sim(COSTS_PIPS["IQ"], **kw), "IQ", name))
    print(pd.DataFrame(iq_rows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "tp_variants_ttp.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    be_df.to_csv(out.with_name("tp_variants_breakeven.csv"), index=False)
    pd.DataFrame(iq_rows).to_csv(out.with_name("tp_variants_iq.csv"), index=False)
    print(f"\nGespeichert: {out} (+ _breakeven, _iq)")


if __name__ == "__main__":
    main()
