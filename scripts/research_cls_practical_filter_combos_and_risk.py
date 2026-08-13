"""Zwei Nachfragen des Users (2026-08-13) auf Basis der jetzt aktiven Defaults
(use_rates_filter=False, min_adx=15.0, sonst unveraendert):

1. Filter-Kombinationen: wie performt die Strategie ohne Trend (inkl. ADX,
   da an use_trend_filter gekoppelt), ohne Cross, und komplett filterlos
   (nur der strukturelle Break/Retest/Fractal-Mechanismus, keine der drei
   Tagesfilter)?
2. Risk-Tabelle: 0.5% / 1% / 2% risk_pct auf 100k-Konto. WICHTIG (im Chat
   offengelegt): das Sizing-Modell ist FIXED-DOLLAR-RISK je Trade
   (risk_amount = account_size * risk_pct, account_size bleibt over die
   gesamte Simulation KONSTANT, kein Comitting/Equity-Wachstum) -- Win-Rate,
   R-Multiples und alle dimensionslosen Kennzahlen sind bei allen drei
   risk_pct-Werten IDENTISCH, nur die Dollar-Betraege skalieren linear.
   Trotzdem sinnvoll als konkrete Referenztabelle fuer die Risk-Management-
   Diskussion (naechster Schritt) -- inkl. schlechtestem Einzeltrade und
   einer einfachen kumulierten Drawdown-Schaetzung (laufende Summe der
   Dollar-PnL in chronologischer Reihenfolge, NICHT compoundend)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def r_stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"{label}: keine Trades")
        return {"label": label, "n_trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins = r[r > 0]
    row = {"label": label, "n_trades": n, "win_rate": len(wins) / n, "avg_r": r.mean(), "total_r": r.sum()}
    print(f"{label}: n={n} WR={row['win_rate']*100:.1f}% avg_R={row['avg_r']:+.3f} total_R={row['total_r']:+.2f}")
    return row


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    args = (eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    print("\n=== 1) Filter-Kombinationen (auf neuer Baseline: Rates bereits aus) ===")
    rows = []
    rows.append(r_stats(simulate_cls_practical(*args), "Aktuell (Trend+ADX, Cross, kein Rates)"))
    rows.append(r_stats(simulate_cls_practical(*args, use_trend_filter=False), "ohne Trend (+ ADX faellt mit weg)"))
    rows.append(r_stats(simulate_cls_practical(*args, use_cross_filter=False), "ohne Cross"))
    rows.append(r_stats(simulate_cls_practical(*args, use_trend_filter=False, use_cross_filter=False), "komplett filterlos"))
    pd.DataFrame(rows).to_csv(Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "filter_combos.csv", index=False)

    print("\n=== 2) Risk-Tabelle 0.5% / 1% / 2% auf 100k-Konto ===")
    risk_rows = []
    for risk_pct in (0.005, 0.01, 0.02):
        trades = simulate_cls_practical(*args, risk_pct=risk_pct)
        trades = trades.sort_values("entry_time").reset_index(drop=True)
        cum = trades["pnl_usd"].cumsum() + 100_000
        running_max = cum.cummax()
        dd = cum - running_max
        max_dd_usd = dd.min()
        worst_trade_usd = trades["pnl_usd"].min()
        best_trade_usd = trades["pnl_usd"].max()
        row = {
            "risk_pct": f"{risk_pct*100:.1f}%",
            "n_trades": len(trades),
            "win_rate": (trades["pnl_usd"] > 0).mean(),
            "total_pnl_usd": trades["pnl_usd"].sum(),
            "final_equity_usd": 100_000 + trades["pnl_usd"].sum(),
            "worst_trade_usd": worst_trade_usd,
            "best_trade_usd": best_trade_usd,
            "max_drawdown_usd": max_dd_usd,
            "max_drawdown_pct_of_100k": max_dd_usd / 100_000 * 100,
        }
        risk_rows.append(row)
        print(f"risk_pct={risk_pct*100:.1f}%: PnL=${row['total_pnl_usd']:+,.0f} "
              f"schlechtester Trade=${worst_trade_usd:+,.0f} bester Trade=${best_trade_usd:+,.0f} "
              f"max DD=${max_dd_usd:+,.0f} ({row['max_drawdown_pct_of_100k']:.2f}% von 100k)")

    pd.DataFrame(risk_rows).to_csv(Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "risk_pct_table.csv", index=False)
    print(f"\nSaved cls_practical/results/filter_combos.csv und risk_pct_table.csv")


if __name__ == "__main__":
    main()
