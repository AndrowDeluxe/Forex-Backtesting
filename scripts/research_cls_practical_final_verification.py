"""Finale Zusammenfassung/Verifikation der aktuellen besten cls_practical-
Konfiguration (User-Anfrage 2026-08-13) -- risk_pct=1% (User-Vorgabe fuer
diese Phase), sonst reine engine.py-Defaults. Baut eine echte Equity-Kurve
aus den tatsaechlichen $-PnL-Werten (NICHT ueber strategy/metrics.py's
summarize(), die auf trades["return_pct"] -- dem rohen Preis-Return, als ob
100% des Kapitals pro Trade eingesetzt wuerden -- basiert und damit NICHT
das tatsaechliche risk_pct-basierte Sizing-Modell dieser Strategie abbildet).
Stattdessen: taegliche $-PnL-Summe, Equity = 100k + kumulierte Summe (fixes
Dollar-Risiko-Modell, kein Comitting -- siehe Chat-Diskussion von gestern
zur Risk-Tabelle), Kennzahlen direkt daraus.

Buy-and-Hold-Vergleich: EUR/USD Spot, 100k unleveraged, 1x, gleicher
Zeitraum -- als Referenzbasis, nicht als "faire" Alternative (FX-Spot-
Buy&Hold hat keine oekonomische Grundlage wie ein Aktienindex, dient hier
nur als Nullhypothese/Referenzpunkt)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
RISK_PCT = 0.01
INITIAL_EQUITY = 100_000.0
TRADING_DAYS_PER_YEAR = 252


def equity_metrics(daily_pnl: pd.Series, label: str) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    daily_ret = equity.pct_change().fillna(0.0)
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    max_dd = dd.min()
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    total_return = equity.iloc[-1] / INITIAL_EQUITY - 1
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd != 0 else float("nan")
    row = {
        "label": label, "final_equity": equity.iloc[-1], "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100, "max_drawdown_pct": max_dd * 100, "sharpe": sharpe, "calmar": calmar,
    }
    print(f"{label}: Endkapital=${row['final_equity']:,.0f} Gesamt-Return={row['total_return_pct']:+.1f}% "
          f"CAGR={row['cagr_pct']:+.2f}% MaxDD={row['max_drawdown_pct']:.2f}% Sharpe={row['sharpe']:.2f} Calmar={row['calmar']:.2f}")
    return row


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_pct=RISK_PCT)
    trades = trades.sort_values("exit_time")

    # tz-naiver Kalendertag als gemeinsamer Schluessel -- trades["exit_time"]
    # und eurusd_m5.index sind Berlin-tz-aware, full_days war das nicht (Bug
    # gefunden 2026-08-13: stiller Reindex-Mismatch liess ALLE Tage auf 0.0
    # fallen statt zu matchen -- .dt.tz_localize(None) statt .dt.floor("D")
    # behebt das).
    full_days = pd.date_range(pd.Timestamp(START), pd.Timestamp(END), freq="D")
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    daily_pnl = trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)

    rows = []
    print(f"\n=== STRATEGIE (cls_practical, risk_pct={RISK_PCT*100:.1f}%, {len(trades)} Trades) ===")
    rows.append(equity_metrics(daily_pnl, "Strategie -- Gesamt"))
    rows.append(equity_metrics(daily_pnl.loc[:SPLIT], "Strategie -- In-Sample"))
    rows.append(equity_metrics(daily_pnl.loc[SPLIT:], "Strategie -- Out-of-Sample"))

    print(f"\n=== BUY & HOLD EUR/USD (Referenz, 100k unleveraged, 1x) ===")
    eurusd_daily = eurusd_m5["close"].copy()
    eurusd_daily.index = eurusd_daily.index.tz_localize(None)
    eurusd_daily = eurusd_daily.resample("1D").last().dropna()
    eurusd_daily = eurusd_daily.reindex(full_days).ffill().dropna()
    bh_price_ret = eurusd_daily.pct_change().fillna(0.0)
    bh_pnl = bh_price_ret * INITIAL_EQUITY  # 1x, kein Hebel
    rows.append(equity_metrics(bh_pnl, "Buy & Hold EUR/USD -- Gesamt"))
    rows.append(equity_metrics(bh_pnl.loc[:SPLIT], "Buy & Hold EUR/USD -- In-Sample"))
    rows.append(equity_metrics(bh_pnl.loc[SPLIT:], "Buy & Hold EUR/USD -- Out-of-Sample"))

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "final_verification_vs_buyhold.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")

    # Jahresaufschluesselung Strategie
    print("\n=== Jahresaufschluesselung Strategie ===")
    t = trades.copy()
    t["year"] = t["exit_time"].dt.year
    yearly = t.groupby("year")["pnl_usd"].sum()
    for year, pnl in yearly.items():
        print(f"  {year}: ${pnl:+,.0f}")


if __name__ == "__main__":
    main()
