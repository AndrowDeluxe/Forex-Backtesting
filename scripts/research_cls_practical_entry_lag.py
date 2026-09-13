"""Quantifiziert den Zeitversatz zwischen Signalbar und Live-Entry bei
cls_practical -- und was er mit der Positionsgroesse macht.

WARUM DIESES SKRIPT: die Kostenvalidierung (scripts/research_cls_practical_
broker_cost_validation.py) zeigt, dass die realen Broker-Kosten (~2,05 Pips
auf TTP) die Strategie zwar Ergebnis kosten, aber allein nicht erklaeren,
warum der Live-Trade vom 2026-09-09 das 2,2-fache seines Budgets verlor. Der
fehlende Faktor steckt woanders:

  Backtest: Einstieg zum Schlusskurs der Signalbar (trigger_level), Stop
            sl_dist darunter. Risiko-Abstand = sl_dist, per Definition.
  Live:     der Bot scannt alle 5 Minuten (data_lake "fast5"-Lane, seit
            2026-09-07 auch fuer cls_practical). Er steigt zu dem Kurs ein,
            der beim NAECHSTEN Scan gilt -- der Stop bleibt aber auf dem
            absoluten Preis aus dem Signal.

Damit ist der reale Risiko-Abstand nicht sl_dist, sondern |Live-Kurs - SL|.
Und weil Funded-Portfolio-Bridge/sizing.py die Lots als
risk_dollars / |Live-Kurs - SL| rechnet, wirkt jede guenstige Kursdrift
zwischen Signalbar und Entry als HEBEL: der Nenner schrumpft, die
Positionsgroesse waechst.

Am 2026-09-09 real passiert: Signal 10:20 (Kurs 1.163967, SL 1.163590,
sl_dist 3,6 Pips), Entry 10:30 zu 1.16380. Abstand nur noch 2,1 Pips, die
Sizing-Referenz sogar nur 1,2 Pips -> 20,8 Lots statt der ~6,9 Lots, die zu
sl_dist gepasst haetten. Nominal ~$2,42 Mio. auf $99.842 Equity.

Dieses Skript prueft, ob das ein Einzelfall war oder die Regel -- ueber alle
historischen Signale, fuer Verzoegerungen von 1 bis 3 M5-Baren.

REIN LESEND, reine Backtest-Auswertung. Kein MT5, keine Order.

Aufruf:
    python scripts/research_cls_practical_entry_lag.py [--start 2018-12-01]
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

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

DEFAULT_START, DEFAULT_END = "2018-12-01", "2026-09-09"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
PIP = 0.0001

# Der Live-Bot riskiert je CLS-Trade 1/6 x 1,5% = 0,25% der Equity
# (challenge_portfolio/paper_bot.py), auf ~100k also ~$250.
RISK_DOLLARS = 250.0
EQUITY = 100_000.0
USD_PER_PIP_PER_LOT = 10.0  # EURUSD, USD als Quote-Waehrung
NOTIONAL_PER_LOT = 100_000.0  # 1 Lot = 100.000 EUR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--lags", type=int, nargs="+", default=[1, 2, 3],
                    help="Verzoegerung in M5-Baren (1 = 5 Min. nach Signalbar)")
    args = ap.parse_args()

    print(f"Lade Daten {args.start}..{args.end} ...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", args.start, args.end)
    other = {p: fetch_major_m15_berlin(p, args.start, args.end) for p in OTHER_MAJORS}
    bund = fetch_rate_instrument_m5_berlin("BUND", args.start, args.end)
    ust = fetch_rate_instrument_m5_berlin("USTBOND", args.start, args.end)

    trades = simulate_cls_practical(eurusd_m5, other, bund, ust)
    if trades.empty:
        print("Keine Trades im Zeitraum.")
        return
    print(f"  {len(trades)} Signale\n")

    close = eurusd_m5["close"]
    pos_of_time = {t: i for i, t in enumerate(eurusd_m5.index)}

    print("=" * 118)
    print("EFFEKTIVER RISIKO-ABSTAND UND POSITIONSGROESSE BEI VERZOEGERTEM EINSTIEG")
    print("=" * 118)
    print(f"  Referenz ohne Verzoegerung: sl_distance im Median "
          f"{(trades['sl_distance'] / PIP).median():.1f} Pips "
          f"-> {RISK_DOLLARS / ((trades['sl_distance'] / PIP).median() * USD_PER_PIP_PER_LOT):.1f} Lots\n")

    rows = []
    for lag in args.lags:
        eff_pips, lots, notional_x, past_sl = [], [], [], 0
        for _, t in trades.iterrows():
            i = pos_of_time.get(t["entry_time"])
            if i is None or i + lag >= len(close):
                continue
            live = float(close.iloc[i + lag])
            d = 1 if t["direction"] == "long" else -1
            eff = (live - t["sl"]) * d  # positiv = SL noch in Risikorichtung entfernt
            if eff <= 0:
                past_sl += 1  # Kurs schon jenseits des Stops -- Trade waere sofort tot
                continue
            eff_p = eff / PIP
            lot = RISK_DOLLARS / (eff_p * USD_PER_PIP_PER_LOT)
            eff_pips.append(eff_p)
            lots.append(lot)
            notional_x.append(lot * NOTIONAL_PER_LOT / EQUITY)

        eff_pips, lots, notional_x = np.array(eff_pips), np.array(lots), np.array(notional_x)
        base_lots = RISK_DOLLARS / ((trades["sl_distance"] / PIP) * USD_PER_PIP_PER_LOT)
        rows.append({
            "Lag (M5-Baren)": lag,
            "Minuten": lag * 5,
            "n": len(eff_pips),
            "Kurs schon hinter SL": past_sl,
            "Eff. Abstand Median (Pips)": float(np.median(eff_pips)),
            "Eff. Abstand p10 (Pips)": float(np.percentile(eff_pips, 10)),
            "Lots Median": float(np.median(lots)),
            "Lots p90": float(np.percentile(lots, 90)),
            "Hebel Median (x Equity)": float(np.median(notional_x)),
            "Hebel p90 (x Equity)": float(np.percentile(notional_x, 90)),
            "Lot-Inflation vs. sl_dist": float(np.median(lots) / base_lots.median()),
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print("\n" + "=" * 118)
    print("WIE OFT WIRD DER EINSTIEG GEFAEHRLICH ENG? (Anteil der Signale je Schwelle)")
    print("=" * 118)
    print("  Gemessener TTP-Round-Trip-Kostenblock: 2,05 Pips. Ein Einstieg, dessen")
    print("  Abstand zum Stop darunter liegt, kann per Konstruktion nicht aufgehen.\n")
    for lag in args.lags:
        eff = []
        for _, t in trades.iterrows():
            i = pos_of_time.get(t["entry_time"])
            if i is None or i + lag >= len(close):
                continue
            d = 1 if t["direction"] == "long" else -1
            eff.append((float(close.iloc[i + lag]) - t["sl"]) * d / PIP)
        eff = np.array(eff)
        n = len(eff)
        print(f"  Lag {lag} ({lag*5:2d} Min., n={n}):")
        for thresh, name in ((0.0, "hinter dem Stop"), (2.05, "< TTP-Kosten"),
                             (4.10, "< 2x TTP-Kosten"), (10.0, "< 10 Pips")):
            share = 100.0 * (eff < thresh).sum() / n if n else 0.0
            print(f"      {name:18}: {(eff < thresh).sum():4d} Signale ({share:5.1f}%)")
        over5 = 100.0 * (RISK_DOLLARS / (np.maximum(eff, 0.01) * USD_PER_PIP_PER_LOT)
                         * NOTIONAL_PER_LOT / EQUITY > 5).sum() / n if n else 0.0
        print(f"      Hebel > 5x Equity : {over5:5.1f}% der Signale")

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "entry_lag_sizing.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


if __name__ == "__main__":
    main()
