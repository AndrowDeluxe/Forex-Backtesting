"""EUR/USD: der Tageskerzen-Zinsfilter als RISIKO-SKALIERUNG statt als
Trade-Gate (User-Anfrage 2026-08-19): "Wie würde sich der Filter als
zusätzliche Confirmation für mehr Risk auswirken? Also quasi Baseline mit 1%
Risk und wenn Filter passen 1,5% Risk pro Trade."

Unterschied zum Gate-Test (research_cls_practical_daily_rate_filter.py):
dort liess use_rates_filter=True NUR "grün"-Tage durch (und cutte damit
~70% der Trades). Hier bleiben ALLE Baseline-Trades erhalten
(use_rates_filter=False, wie im Live-Pfad), nur die POSITIONSGROESSE wird
pro Tag skaliert - der bereits 2026-08-18 gebaute, aber bis jetzt nie
genutzte `risk_multiplier`-Parameter von simulate_cls_practical().

Wichtiger Methodik-Punkt: R-Vielfache (pnl_usd/risk_amount_usd) sind SKALEN-
INVARIANT - eine reine Risiko-Skalierung aendert avg_R pro Trade NICHT
(dieselbe SL-Distanz, nur mehr/weniger Dollar pro Punkt Bewegung). Der
gesamte Sinn/Nutzen einer Risk-Skalierung zeigt sich ausschliesslich in den
$-Kennzahlen der EQUITY-KURVE (Sharpe/Calmar/MaxDD/Gesamt-PnL) - deshalb hier
dieselbe Equity-Methodik wie research_cls_practical_point0900_full_verification.py/
research_cls_practical_final_verification.py, NICHT avg_R-Vergleiche."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from cls_practical.rates import compute_daily_rate_score, classify_rates_ampel
from strategy.cls_advanced import compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in cls_advanced.PAIRS if p != "EURUSD"]
BASE_RISK_PCT = 0.01  # User-Vorgabe fuer diesen Test: 1% Basis-Risiko
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0


def daily_pnl_series(trades: pd.DataFrame, start: str, end: str) -> pd.Series:
    full_days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    if len(trades) == 0:
        return pd.Series(0.0, index=full_days)
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    return trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)


def equity_metrics(daily_pnl: pd.Series) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    daily_ret = equity.pct_change().fillna(0.0)
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    max_dd = dd.min()
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd not in (0, float("nan")) else float("nan")
    return {"final_equity": equity.iloc[-1], "total_pnl": daily_pnl.sum(), "cagr_pct": cagr * 100,
            "max_drawdown_pct": max_dd * 100, "sharpe": sharpe, "calmar": calmar}


def report(label: str, trades: pd.DataFrame) -> dict:
    row = {"label": label, "n": len(trades)}
    for period, p_start, p_end in (("gesamt", START, END), ("is", START, SPLIT), ("oos", SPLIT, END)):
        if period == "gesamt":
            t = trades
        elif period == "is":
            t = trades[trades["entry_time"].dt.tz_localize(None) < SPLIT]
        else:
            t = trades[trades["entry_time"].dt.tz_localize(None) >= SPLIT]
        m = equity_metrics(daily_pnl_series(t, p_start, p_end))
        for k, v in m.items():
            row[f"{period}_{k}"] = v
    print(f"  {label:34s}: n={row['n']:>3d} | Gesamt PnL=${row['gesamt_total_pnl']:+,.0f} CAGR={row['gesamt_cagr_pct']:+.2f}% "
          f"MaxDD={row['gesamt_max_drawdown_pct']:.2f}% Sharpe={row['gesamt_sharpe']:.2f} Calmar={row['gesamt_calmar']:.2f} "
          f"| IS Sharpe={row['is_sharpe']:.2f} PnL=${row['is_total_pnl']:+,.0f} "
          f"| OOS Sharpe={row['oos_sharpe']:.2f} PnL=${row['oos_total_pnl']:+,.0f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5)
    direction = daily["direction"]

    print(f"\n{'='*110}\nFLACHES {BASE_RISK_PCT*100:.0f}%-RISIKO, KEINE SKALIERUNG (Referenz)\n{'='*110}")
    flat_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                          use_rates_filter=False, risk_pct=BASE_RISK_PCT)
    rows = [report(f"Flach {BASE_RISK_PCT*100:.0f}% (keine Skalierung)", flat_trades)]

    print(f"\n{'='*110}\nRISIKO-SKALIERUNG: {BASE_RISK_PCT*100:.0f}% Basis -> hoeher bei Zins-Bestaetigung ('gruen')\n{'='*110}")
    lag_days = 2  # dieselbe Konfiguration, die sich beim Gate-Test/Robustheits-Check bewaehrt hat
    score = compute_daily_rate_score(bund_m5, ustbond_m5, lag_days=lag_days)

    for z_threshold in (0.0, 0.25, 0.5):
        ampel = classify_rates_ampel(score, direction, z_window=60, z_threshold=z_threshold)
        confirmed_share = (ampel == "grün").mean() * 100
        for mult in (1.25, 1.5, 1.75):
            risk_mult = pd.Series(1.0, index=ampel.index)
            risk_mult[ampel == "grün"] = mult
            label = f"lag={lag_days}d z>={z_threshold} {mult}x auf 'gruen' ({confirmed_share:.0f}% d. Tage)"
            trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                             use_rates_filter=False, risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)
            rows.append(report(label, trades))

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_daily_rate_risk_scaling.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")

    print(f"\n{'='*110}\nHauptvergleich: Flach 1% vs. 1%->1.5% bei z>=0.5 (User-Beispiel)\n{'='*110}")
    flat = df[df["label"].str.startswith("Flach")].iloc[0]
    main_variant = df[df["label"].str.contains("z>=0.5 1.5x")].iloc[0]
    for period in ("gesamt", "is", "oos"):
        print(f"  {period.upper():6s}: Flach PnL=${flat[f'{period}_total_pnl']:+,.0f} Sharpe={flat[f'{period}_sharpe']:.2f} "
              f"MaxDD={flat[f'{period}_max_drawdown_pct']:.2f}%  ->  Skaliert PnL=${main_variant[f'{period}_total_pnl']:+,.0f} "
              f"Sharpe={main_variant[f'{period}_sharpe']:.2f} MaxDD={main_variant[f'{period}_max_drawdown_pct']:.2f}%")


if __name__ == "__main__":
    main()
