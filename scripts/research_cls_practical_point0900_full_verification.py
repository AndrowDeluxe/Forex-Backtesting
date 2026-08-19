"""Vollstaendige EUR/USD-Verifikation des neuen Halte-Test-Checkpoints 09:00
(User-Entscheidung 2026-08-19, nach dem Feinraster-Sweep
scripts/research_cls_practical_holdtest_timing_finegrid.py: point_09:00 war
die einzige Konfiguration, die die 09:15-Baseline gleichzeitig auf IS UND
OOS schlaegt): ALT (09:15) vs. NEU (09:00), jeweils aufgeschluesselt nach
Setup (Gesamt/Continuation/Reversal) x Zeitraum (Gesamt/In-Sample/
Out-of-Sample), mit vollem Kennzahlenset (n, Win-Rate, avg_R, Profit-Factor,
Gesamt-PnL sowie CAGR/Max-Drawdown/Sharpe/Calmar auf der taeglichen
$-PnL-Equity-Kurve -- gleiche Methodik wie
scripts/research_cls_practical_final_verification.py, NICHT
strategy/metrics.py's summarize(), das auf dem rohen Preis-Return statt dem
tatsaechlichen risk_pct-Sizing basiert).

Alle uebrigen Parameter bleiben auf den validierten engine.py-Defaults
(SMA100+ADX>=15 Trend, Rates-Filter aus, Cross-Filter an, AND-gated,
TP=0.35xADR14, SL=Fraktal-Extrem mit 1.0x-ATR-Floor, risk_pct=0.5%) -
NUR test_hour unterscheidet ALT von NEU, damit der Effekt sauber isoliert
bleibt."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
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
    return {"cagr_pct": cagr * 100, "max_drawdown_pct": max_dd * 100, "sharpe": sharpe, "calmar": calmar}


def slice_stats(trades: pd.DataFrame, period_start: str, period_end: str) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "win_rate": float("nan"), "avg_r": float("nan"), "profit_factor": float("nan"),
                "total_pnl": 0.0, "cagr_pct": float("nan"), "max_drawdown_pct": float("nan"),
                "sharpe": float("nan"), "calmar": float("nan")}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    row = {"n": n, "win_rate": win_rate * 100, "avg_r": r.mean(), "profit_factor": pf,
           "total_pnl": trades["pnl_usd"].sum()}
    row.update(equity_metrics(daily_pnl_series(trades, period_start, period_end)))
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + Rates)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    configs = [("ALT (Haltetest 09:15)", 9.25), ("NEU (Haltetest 09:00)", 9.0)]
    setups = [("Gesamt (Conti+Rev)", None), ("Continuation", "continuation"), ("Reversal", "reversal")]
    # period filtering below uses entry_time; the (start,end) pair here is
    # only for the equity-curve day-range
    periods = [("Gesamt", START, END), ("In-Sample", START, SPLIT), ("Out-of-Sample", SPLIT, END)]

    rows = []
    for cfg_label, test_hour in configs:
        print(f"\n{'='*100}\n{cfg_label}\n{'='*100}")
        trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, test_hour=test_hour)
        trades["entry_date_naive"] = trades["entry_time"].dt.tz_localize(None)

        for setup_label, setup_filter in setups:
            t_setup = trades if setup_filter is None else trades[trades["setup"] == setup_filter]
            print(f"\n  --- {setup_label} ---")
            for period_label, p_start, p_end in periods:
                if period_label == "Gesamt":
                    t_slice = t_setup
                elif period_label == "In-Sample":
                    t_slice = t_setup[t_setup["entry_date_naive"] < SPLIT]
                else:
                    t_slice = t_setup[t_setup["entry_date_naive"] >= SPLIT]
                st = slice_stats(t_slice, p_start, p_end)
                print(f"    {period_label:14s}: n={st['n']:>3d} WinRate={st['win_rate']:5.1f}% avg_R={st['avg_r']:+.3f} "
                      f"PF={st['profit_factor']:.2f} PnL=${st['total_pnl']:+,.0f} | "
                      f"CAGR={st['cagr_pct']:+.2f}% MaxDD={st['max_drawdown_pct']:.2f}% "
                      f"Sharpe={st['sharpe']:.2f} Calmar={st['calmar']:.2f}")
                rows.append({"config": cfg_label, "setup": setup_label, "period": period_label, **st})

    out = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_point0900_full_verification.csv"
    out.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
