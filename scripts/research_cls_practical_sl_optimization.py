"""SL-Varianten fuer cls_practical unter ECHTEN Broker-Kosten (Nutzerfrage
2026-09-09: "Macht ein dynamisch groesserer SL Sinn oder ein durch die
durchschnittliche Session-Volatilitaet gemittelter fester SL?").

AUSGANGSLAGE (siehe knowledge/projects/cls-practical-kostenvalidierung.md):
bei den gemessenen TTP-Round-Trip-Kosten von 2,05 Pips faellt PF von 1,57 auf
1,12 und Ø R von 0,36 auf 0,10 -- Breakeven liegt bei ~2,70 Pips, es bleiben
also 0,65 Pips Luft. Der gesamte Schaden sitzt in den engen Stops: Trades mit
sl_dist < 6,15 Pips (42 % aller Trades) haben Ø R -0,238, die uebrigen +0,343.

Der bestehende Schutz `min_sl_atr_mult = 1.0 x ATR(M5)` greift nicht, weil er
am MOMENTANWERT der Einstiegsbar haengt und in ruhigen Minuten mitschrumpft.

GETESTETE VARIANTEN (alle neu in cls_practical/engine.py, Defaults unveraendert):
  A "drop"   -- absoluter Pip-Boden, Trade wird VERWORFEN wenn zu eng.
                Weniger Trades, dafuer nur noch tragfaehige.
  B "widen"  -- absoluter Pip-Boden, Stop wird stattdessen AUFGEWEITET.
                Gleiche Trade-Zahl, kleinere Position (units = risk/sl_dist),
                aber schlechteres R:R weil das TP-Ziel (adr_mult x ADR) bleibt.
  C ATR-Mult -- der bestehende relative Boden, nur hoeher (1,5-3,0x), je in
                "drop" und "widen".
  D Session  -- struktureller Stop KOMPLETT ersetzt durch
                mult x (gleitender 20-Tage-Mittelwert des Median-ATR(M5) im
                Handelsfenster). Das ist der "durch die durchschnittliche
                Session-Volatilitaet gemittelte" Stop aus der Nutzerfrage:
                unabhaengig von der Zufallsvolatilitaet der Einstiegsminute,
                aber mitwandernd ueber Volatilitaetsregime. Strikt
                vergangenheitsbasiert, kein Lookahead.

BEWERTUNG: primaer unter TTP-Kosten (2,05 Pips -- der harte Fall; IQ ist mit
1,30 Pips deutlich entspannter). Ausgewiesen wird IMMER auch das Out-of-Sample
ab 2022-06-01 und der erzeugte Hebel, weil genau der am 2026-09-09 zum Problem
wurde (20,8 Lots = ~24x Equity).

Aufruf:
    python scripts/research_cls_practical_sl_optimization.py [--start 2018-12-01]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)

DEFAULT_START, DEFAULT_END = "2018-12-01", "2026-09-10"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
PIP = 0.0001

RISK_PCT = 0.0025          # 1/6 x 1,5 % -- das real gehandelte CLS-Risiko
INITIAL_EQUITY = 100_000.0
RISK_DOLLARS = INITIAL_EQUITY * RISK_PCT
USD_PER_PIP_PER_LOT = 10.0

# Gemessene Round-Trip-Kosten (scripts/measure_broker_spreads.py, 2026-09-09)
COSTS_PIPS = {"TTP": 2.05, "IQ": 1.30}
BREAKEVEN_HINT = 2.70


def pips_to_bps(pips: float, price: float) -> float:
    return pips * PIP / price * 10_000


def evaluate(trades: pd.DataFrame, label: str, variant: str) -> dict:
    if trades.empty:
        return {"Variante": variant, "Setup": label, "Trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    ex = trades["exit_time"].dt.tz_localize(None)
    r_oos = r[ex >= SPLIT]
    r_is = r[ex < SPLIT]
    wins = trades[trades["pnl_usd"] > 0]
    gl = abs(trades[trades["pnl_usd"] <= 0]["pnl_usd"].sum())

    daily = trades.groupby(ex.dt.floor("D"))["pnl_usd"].sum().sort_index()
    equity = INITIAL_EQUITY + daily.cumsum()
    max_dd = float((equity / equity.cummax() - 1.0).min())

    sl_pips = trades["sl_distance"] / PIP
    lots = RISK_DOLLARS / (sl_pips * USD_PER_PIP_PER_LOT)  # = Hebel in x Equity bei 100k

    return {
        "Variante": variant,
        "Setup": label,
        "Trades": len(trades),
        "Treffer%": 100.0 * len(wins) / len(trades),
        "PF": (wins["pnl_usd"].sum() / gl) if gl > 0 else float("inf"),
        "Ø R": float(r.mean()),
        "Ø R (IS)": float(r_is.mean()) if len(r_is) else float("nan"),
        "Ø R (OOS)": float(r_oos.mean()) if len(r_oos) else float("nan"),
        "PnL $": float(trades["pnl_usd"].sum()),
        "MaxDD %": 100.0 * max_dd,
        "SL med (Pips)": float(sl_pips.median()),
        "SL p10": float(sl_pips.quantile(0.10)),
        "Hebel med": float(lots.median()),
        "Hebel p90": float(lots.quantile(0.90)),
        "Hebel max": float(lots.max()),
    }


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

    variants: list[tuple[str, str, dict]] = [("Baseline", "min_sl_atr_mult=1.0, drop", {})]
    for p in (4, 5, 6, 7, 8, 10):
        variants.append(("A Pip-Boden (drop)", f"min_sl_pips={p}", {"min_sl_pips": p}))
    for p in (4, 5, 6, 7, 8, 10):
        variants.append(("B Pip-Boden (widen)", f"min_sl_pips={p}",
                         {"min_sl_pips": p, "sl_floor_mode": "widen"}))
    for m in (1.5, 2.0, 2.5, 3.0):
        variants.append(("C ATR-Mult (drop)", f"min_sl_atr_mult={m}", {"min_sl_atr_mult": m}))
    for m in (1.5, 2.0, 2.5, 3.0):
        variants.append(("C ATR-Mult (widen)", f"min_sl_atr_mult={m}",
                         {"min_sl_atr_mult": m, "sl_floor_mode": "widen"}))
    for m in (1.0, 1.5, 2.0, 2.5, 3.0):
        variants.append(("D Session-Vol-SL", f"session_sl_mult={m}", {"session_sl_mult": m}))

    print("=" * 200)
    print(f"UNTER TTP-KOSTEN ({COSTS_PIPS['TTP']} Pips Round-Trip; Breakeven der Baseline lag bei ~{BREAKEVEN_HINT} Pips)")
    print("=" * 200)
    rows = []
    for variant, label, kw in variants:
        rows.append(evaluate(sim(COSTS_PIPS["TTP"], **kw), label, variant))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # Kandidaten: OOS positiv, mindestens die Haelfte der Baseline-Trades,
    # und Hebel p90 unter 10x Equity. Die Trade-Zahl-Bedingung verhindert,
    # dass eine Variante nur deshalb glaenzt, weil sie fast alles wegfiltert.
    base_n = df.iloc[0]["Trades"]
    cand = df[(df["Ø R (OOS)"] > df.iloc[0]["Ø R (OOS)"])
              & (df["Trades"] >= base_n * 0.5)
              & (df["Hebel p90"] < 10.0)].copy()
    cand = cand.sort_values("Ø R (OOS)", ascending=False)

    print("\n" + "=" * 200)
    print("KANDIDATEN (OOS besser als Baseline, >=50 % der Trades, Hebel p90 < 10x Equity)")
    print("=" * 200)
    if cand.empty:
        print("  Keine Variante erfuellt alle drei Bedingungen.")
    else:
        print(cand.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    top = (cand if not cand.empty else df.sort_values("Ø R (OOS)", ascending=False)).head(5)
    print("\n" + "=" * 200)
    print(f"GEGENPROBE DER TOP-{len(top)} UNTER IQ-KOSTEN ({COSTS_PIPS['IQ']} Pips)")
    print("=" * 200)
    lookup = {(v, l): kw for v, l, kw in variants}
    iq_rows = [evaluate(sim(COSTS_PIPS["IQ"]), "min_sl_atr_mult=1.0, drop", "Baseline")]
    for _, row in top.iterrows():
        kw = lookup.get((row["Variante"], row["Setup"]))
        if kw is None:
            continue
        iq_rows.append(evaluate(sim(COSTS_PIPS["IQ"], **kw), row["Setup"], row["Variante"]))
    print(pd.DataFrame(iq_rows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "sl_optimization_ttp.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    pd.DataFrame(iq_rows).to_csv(out.with_name("sl_optimization_iq.csv"), index=False)
    print(f"\nGespeichert: {out}\n           {out.with_name('sl_optimization_iq.csv')}")


if __name__ == "__main__":
    main()
