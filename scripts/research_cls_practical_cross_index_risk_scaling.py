"""EUR/USD: dasselbe Risiko-Skalierungs-Prinzip wie beim Zinsfilter (siehe
research_cls_practical_daily_rate_risk_scaling.py, 2026-08-19 uebernommen)
jetzt auf den Cross-Filter (compute_cross_vote_confirmation) und den
Index-Filter (compute_currency_index_confirmation) angewendet - User-
Anfrage: "Teste ein aehnliches Prinzip auf den gebauten Cross Filter und
den Indice Filter."

Beide waren als hartes GATE im Fenster/Schwellen-Sweep (Sweep A,
scripts/research_cls_practical_window_threshold_holdtest_sweep.py) ohne
klaren Mehrwert - genau wie der Zinsfilter dort als Gate keinen Mehrwert
zeigte (siehe research_cls_practical_daily_rate_filter.py, "and"-Modus
massiv weniger Trades), aber als reine Risiko-Skalierung (volle Stichprobe
erhalten) klar half. Hypothese hier: derselbe Effekt koennte sich
wiederholen.

Setup identisch zum Zinsfilter-Test: use_cross_filter/use_rates_filter/
use_trend_filter bleiben auf den validierten Baseline-Defaults (Trend an,
Cross an ueber die ORIGINALE compute_cross_confirmation, Rates aus) -
NICHTS an der Trade-Auswahl aendert sich. Nur risk_multiplier (1% Basis)
wird aus dem jeweiligen NEUEN Filter abgeleitet - Fenster "day_start",
Checkpoint 9.0 (aktueller Default)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.currency_strength import compute_cross_vote_confirmation, compute_currency_index_confirmation
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
BASE_RISK_PCT = 0.01
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0

EURUSD_BASKET = ["EURGBP", "EURCHF", "EURCAD", "EURAUD", "EURJPY",
                 "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]


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
    return {"total_pnl": daily_pnl.sum(), "cagr_pct": cagr * 100, "max_drawdown_pct": max_dd * 100,
            "sharpe": sharpe, "calmar": calmar}


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
    print(f"  {label:42s}: n={row['n']:>3d} | Gesamt PnL=${row['gesamt_total_pnl']:+,.0f} "
          f"Sharpe={row['gesamt_sharpe']:.2f} Calmar={row['gesamt_calmar']:.2f} MaxDD={row['gesamt_max_drawdown_pct']:.2f}% "
          f"| IS Sharpe={row['is_sharpe']:.2f} | OOS Sharpe={row['oos_sharpe']:.2f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 10er-Referenzkorb M15 + Rates)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    ref_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in EURUSD_BASKET}
    other_majors_m15 = {p: ref_m15[p] for p in cls_advanced.PAIRS if p != "EURUSD"}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5)
    direction = daily["direction"]

    print(f"\n{'='*115}\nFLACHES {BASE_RISK_PCT*100:.0f}%-RISIKO, KEINE SKALIERUNG (Referenz)\n{'='*115}")
    flat_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, risk_pct=BASE_RISK_PCT)
    rows = [report(f"Flach {BASE_RISK_PCT*100:.0f}% (keine Skalierung)", flat_trades)]

    print(f"\n{'='*115}\nCROSS-FILTER als Risiko-Skalierung (Fenster=day_start)\n{'='*115}")
    for threshold in (0.4, 0.5, 0.6):
        conf = compute_cross_vote_confirmation("EURUSD", direction, ref_m15, confirm_threshold=threshold)
        confirmed_share = conf["confirmed"].mean() * 100
        for mult in (1.25, 1.5, 1.75):
            risk_mult = pd.Series(1.0, index=conf.index)
            risk_mult[conf["confirmed"]] = mult
            label = f"cross thr={threshold} {mult}x ({confirmed_share:.0f}% d. Tage)"
            trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                             risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)
            rows.append({**report(label, trades), "family": "cross", "threshold": threshold, "mult": mult})

    print(f"\n{'='*115}\nINDEX-FILTER als Risiko-Skalierung (liquiditaetsgewichtet, Fenster=day_start)\n{'='*115}")
    idx_conf = compute_currency_index_confirmation("EURUSD", direction, ref_m15)
    confirmed_share = idx_conf["confirmed"].mean() * 100
    for mult in (1.25, 1.5, 1.75):
        risk_mult = pd.Series(1.0, index=idx_conf.index)
        risk_mult[idx_conf["confirmed"]] = mult
        label = f"index {mult}x ({confirmed_share:.0f}% d. Tage)"
        trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                                         risk_pct=BASE_RISK_PCT, risk_multiplier=risk_mult)
        rows.append({**report(label, trades), "family": "index", "mult": mult})

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_cross_index_risk_scaling.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")

    flat = df[df["label"].str.startswith("Flach")].iloc[0]
    print(f"\n{'='*115}\nZUSAMMENFASSUNG: Sharpe/Calmar/MaxDD relativ zur Flach-1%-Referenz\n{'='*115}")
    print(f"  Referenz (flach)                         : Sharpe={flat['gesamt_sharpe']:.2f} Calmar={flat['gesamt_calmar']:.2f} MaxDD={flat['gesamt_max_drawdown_pct']:.2f}%")
    for _, r in df[df["label"] != flat["label"]].iterrows():
        better = "besser" if (r["gesamt_sharpe"] > flat["gesamt_sharpe"] and r["gesamt_calmar"] > flat["gesamt_calmar"]) else ""
        print(f"  {r['label']:42s}: Sharpe={r['gesamt_sharpe']:.2f} Calmar={r['gesamt_calmar']:.2f} MaxDD={r['gesamt_max_drawdown_pct']:.2f}% {better}")


if __name__ == "__main__":
    main()
