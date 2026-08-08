"""Prop-firm-compliance check for the Gold-Bitcoin dual momentum rotation:
fixed-fractional risk sizing (0.5% of equity per trade) to an ATR-based
stop-loss, monitored on daily closes, tested against TTP's actual funded-
account rules (3% max daily drawdown, 7% max total drawdown) rather than
the plain vol-capped version's weekly-only risk control.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_bitcoin_dual_momentum.data import fetch_daily_ohlc_gold_btc, fetch_weekly_gold_btc
from gold_bitcoin_dual_momentum.risk_engine import majority_composite_position, simulate_risk_based

START, END = "2017-08-20", "2026-07-29"
WARMUP_WEEKS = 40
TTP_MAX_DAILY_DD = 0.03
TTP_MAX_TOTAL_DD = 0.07

RISK_SCENARIOS = [
    {"risk_pct": 0.005, "atr_mult": 3.0, "label": "0.5% Risiko, 3x ATR-Stop"},
    {"risk_pct": 0.005, "atr_mult": 2.0, "label": "0.5% Risiko, 2x ATR-Stop"},
    {"risk_pct": 0.0025, "atr_mult": 3.0, "label": "0.25% Risiko, 3x ATR-Stop"},
    {"risk_pct": 0.01, "atr_mult": 3.0, "label": "1.0% Risiko, 3x ATR-Stop"},
    {"risk_pct": 0.015, "atr_mult": 3.0, "label": "1.5% Risiko, 3x ATR-Stop"},
    {"risk_pct": 0.02, "atr_mult": 3.0, "label": "2.0% Risiko, 3x ATR-Stop"},
    {"risk_pct": 0.025, "atr_mult": 3.0, "label": "2.5% Risiko, 3x ATR-Stop"},
]


def metrics_from_daily(daily_returns: pd.Series, equity: pd.Series) -> dict:
    r = daily_returns.dropna()
    n_years = len(r) / 252
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float("nan")
    dd = (equity / equity.cummax() - 1)
    max_total_dd = dd.min()
    max_daily_loss = r.min()
    n_daily_breaches = (r < -TTP_MAX_DAILY_DD).sum()
    return {
        "ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe,
        "max_total_dd": max_total_dd, "max_daily_loss": max_daily_loss,
        "n_daily_breaches": n_daily_breaches, "n_days": len(r),
    }


def fmt(m: dict) -> str:
    daily_ok = "OK" if m["max_daily_loss"] > -TTP_MAX_DAILY_DD else "BREACH"
    total_ok = "OK" if m["max_total_dd"] > -TTP_MAX_TOTAL_DD else "BREACH"
    return (
        f"Return={m['ann_return']:+.2%}  Sharpe={m['sharpe']:.2f}  "
        f"MaxTotalDD={m['max_total_dd']:.2%} [{total_ok} vs -{TTP_MAX_TOTAL_DD:.0%}]  "
        f"WorstDay={m['max_daily_loss']:.2%} [{daily_ok} vs -{TTP_MAX_DAILY_DD:.0%}]  "
        f"Tagesbreaches={m['n_daily_breaches']}/{m['n_days']}"
    )


def main():
    print(f"Fetching weekly + daily OHLC GOLD/BTC {START} -> {END} ...")
    weekly = fetch_weekly_gold_btc(START, END)
    daily = fetch_daily_ohlc_gold_btc(START, END)

    decision = majority_composite_position(weekly, lookbacks=(4, 8, 12))
    decision = decision.iloc[WARMUP_WEEKS:]
    print(f"{len(decision)} Wochenentscheidungen ab {decision.index[0].date()}")
    print(f"Verteilung: {decision.value_counts().to_dict()}")

    print("\n" + "=" * 100)
    print(f"TTP-COMPLIANCE-CHECK (Limits: {TTP_MAX_DAILY_DD:.0%} Tages-DD / {TTP_MAX_TOTAL_DD:.0%} Gesamt-DD)")
    print("=" * 100)
    for scenario in RISK_SCENARIOS:
        sim = simulate_risk_based(
            daily, decision, risk_pct=scenario["risk_pct"], atr_mult=scenario["atr_mult"], starting_equity=100_000.0,
        )
        m = metrics_from_daily(sim["daily_return"], sim["equity"])
        avg_notional = sim.loc[sim["asset"] != "cash", "notional_fraction"].mean()
        n_stops = int(sim["stopped_out_today"].sum())
        print(f"  {scenario['label']:<30}{fmt(m)}")
        print(f"      -> avg. Positionsgroesse wenn investiert: {avg_notional:.1%} des Kontos, Stop-Outs: {n_stops}")

    print(
        "\nHinweis: Tagesverlust hier = Equity-Aenderung Schlusskurs-zu-Schlusskurs (naeherungsweise, da\n"
        "keine Intraday-Daten vorliegen) -- ein echter Stop kann bei Gaps (v.a. Bitcoin-Wochenende) "
        "schlechter fuellen als hier angenommen. Gold hat keine Wochenend-Kurse; wird Bitcoin uebers\n"
        "Wochenende gehalten, kann diese Simulation (wie ein echtes Konto mit geschlossener FX/Metall-\n"
        "Plattform) erst am naechsten gemeinsamen Handelstag reagieren."
    )


if __name__ == "__main__":
    main()
