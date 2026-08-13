"""Filter-Lockerung fuer cls_practical (User-Anfrage, 2026-08-12): der
Funnel-Befund (research_cls_practical_funnel.py) zeigt, dass die strikte
UND-Verknuepfung der drei Tagesfilter (Trend/Rates/Crosses) der Haupt-
Flaschenhals fuer die Trade-Anzahl ist (nur 16.3% aller Tage werden
Kandidat). Dieses Skript testet:

1. filter_mode="and" (Status quo) vs. "majority" (2 von 3 muessen stimmen)
   -- jeweils Voll (Cont.+Rev.) und Reversal-Only.
2. Leave-one-out je Filter (use_trend_filter/use_rates_filter/
   use_cross_filter=False), AND-Modus -- Trend-Ergebnis bereits aus einer
   frueheren Session bekannt (24.1% WR / -11,729$ fuer die 112 zusaetzlichen
   Trades), hier zum Vergleich mit Rates/Crosses neu erhoben.
3. Kleine Parameter-Variation (sma_window, rates_z_window) im
   Majority-Modus -- lohnt sich Retuning, sobald mehr Trades durchkommen?

Alle Varianten reporten zusaetzlich das R-Multiple (pnl_usd/risk_amount_usd
ist exakt R, da risk_amount_usd pro Trade konstant ist), nicht nur
Win-Rate/PF -- Nutzeranliegen: niedrige Win-Rate bei wenig Trades macht
misstrauisch, das R-Profil zeigt ob es trotzdem eine gesunde Kante ist."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"{label}: keine Trades")
        return {"label": label, "n_trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins, losses = r[r > 0], r[r <= 0]
    row = {
        "label": label, "n_trades": n, "trades_per_year": n / ((pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25),
        "win_rate": len(wins) / n, "avg_r": r.mean(),
        "avg_win_r": wins.mean() if len(wins) else float("nan"),
        "avg_loss_r": losses.mean() if len(losses) else float("nan"),
        "total_r": r.sum(), "total_pnl_usd": trades["pnl_usd"].sum(),
    }
    print(f"{label}: n={n} ({row['trades_per_year']:.1f}/Jahr) WR={row['win_rate']*100:.1f}% "
          f"avg_R={row['avg_r']:+.3f} (win={row['avg_win_r']:+.2f}R loss={row['avg_loss_r']:+.2f}R) "
          f"total_R={row['total_r']:+.2f} PnL=${row['total_pnl_usd']:+,.0f}")
    return row


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    args = (eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    rows = []

    # min_adx explizit auf None gepinnt (2026-08-12): eine PARALLELE Session
    # hat den Default zwischenzeitlich auf 15.0 geaendert (eigener Sweep-Fund,
    # siehe engine.py-Docstring) -- fuer diesen Sweep bewusst isoliert von
    # dieser Erweiterung, um exakt die urspruengliche 3-Filter-Frage
    # (Trend/Rates/Crosses, AND vs. Majority) zu beantworten, unabhaengig
    # vom ADX-Zusatzfilter. Auf Nutzerwunsch, statt den neuen Default zu
    # uebernehmen.
    NO_ADX = {"min_adx": None}

    print("\n=== 1) AND vs. Majority (2-von-3) ===")
    for allowed, setup_label in [(("continuation", "reversal"), "Voll"), (("reversal",), "Reversal-Only")]:
        for mode in ("and", "majority"):
            t = simulate_cls_practical(*args, filter_mode=mode, allowed_setups=allowed, **NO_ADX)
            rows.append(stats(t, f"{setup_label} / filter_mode={mode}"))

    print("\n=== 2) Leave-one-out je Filter (AND-Modus, Voll) ===")
    baseline = simulate_cls_practical(*args, **NO_ADX)
    rows.append(stats(baseline, "Baseline (alle 3 Filter aktiv, ohne ADX-Gate)"))
    t_no_trend = simulate_cls_practical(*args, use_trend_filter=False, **NO_ADX)
    rows.append(stats(t_no_trend, "ohne Trend-Filter"))
    t_no_rates = simulate_cls_practical(*args, use_rates_filter=False, **NO_ADX)
    rows.append(stats(t_no_rates, "ohne Rates-Filter"))
    t_no_cross = simulate_cls_practical(*args, use_cross_filter=False, **NO_ADX)
    rows.append(stats(t_no_cross, "ohne Cross-Filter"))

    print("\n=== 3) Parameter-Variation im Majority-Modus (Voll) ===")
    for sma in (50, 100, 150, 200):
        t = simulate_cls_practical(*args, filter_mode="majority", sma_window=sma, **NO_ADX)
        rows.append(stats(t, f"majority, sma_window={sma}"))
    for zw in (30, 60, 90, 120):
        t = simulate_cls_practical(*args, filter_mode="majority", rates_z_window=zw, **NO_ADX)
        rows.append(stats(t, f"majority, rates_z_window={zw}"))

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results"
    out_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path / "filter_relaxation_sweep.csv", index=False)
    print(f"\nSaved {out_path / 'filter_relaxation_sweep.csv'}")


if __name__ == "__main__":
    main()
