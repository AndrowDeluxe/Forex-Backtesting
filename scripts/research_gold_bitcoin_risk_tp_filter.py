"""Follow-up to research_gold_bitcoin_risk_based.py: can adding a take-profit,
a breakeven-move, and a signal-confidence filter (unanimous 3/3 lookback
agreement instead of majority 2/3) allow a TIGHTER ATR stop without more
whipsaw - and does that combination let us push risk_pct higher while
staying inside TTP's 3% daily / 7% total drawdown limits?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_bitcoin_dual_momentum.data import fetch_daily_ohlc_gold_btc, fetch_weekly_gold_btc
from gold_bitcoin_dual_momentum.risk_engine import composite_position, simulate_risk_based

START, END = "2017-08-20", "2026-07-29"
WARMUP_WEEKS = 40
TTP_MAX_DAILY_DD = 0.03
TTP_MAX_TOTAL_DD = 0.07

SCENARIOS = [
    {"label": "Baseline: 3xATR, majority, kein TP/BE",        "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": None, "be_trigger_r": None, "risk_pct": 0.01},
    {"label": "+ Breakeven 0.5R",                              "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": None, "be_trigger_r": 0.5,  "risk_pct": 0.01},
    {"label": "+ TP 1.5R",                                     "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": 1.5,  "be_trigger_r": None, "risk_pct": 0.01},
    {"label": "+ TP 1.5R + BE 0.5R",                           "min_agree": 2, "atr_mult": 3.0, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.01},
    {"label": "2xATR + TP 1.5R + BE 0.5R",                     "min_agree": 2, "atr_mult": 2.0, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.01},
    {"label": "2xATR + TP 1.5R + BE 0.5R + Unanimous-Filter",  "min_agree": 3, "atr_mult": 2.0, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.01},
    {"label": "^ selbe Kombi, Risiko 1.5%",                    "min_agree": 3, "atr_mult": 2.0, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.015},
    {"label": "^ selbe Kombi, Risiko 2.0%",                    "min_agree": 3, "atr_mult": 2.0, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.02},
    {"label": "1.5xATR + TP 1.5R + BE 0.5R + Unanimous, 1.5%", "min_agree": 3, "atr_mult": 1.5, "tp_r_mult": 1.5,  "be_trigger_r": 0.5,  "risk_pct": 0.015},
]


def metrics_from_daily(daily_returns: pd.Series, equity: pd.Series) -> dict:
    r = daily_returns.dropna()
    n_years = len(r) / 252
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float("nan")
    dd = equity / equity.cummax() - 1
    return {
        "ann_return": ann_return, "sharpe": sharpe,
        "max_total_dd": dd.min(), "max_daily_loss": r.min(), "n_days": len(r),
    }


def fmt(m: dict) -> str:
    daily_ok = "OK" if m["max_daily_loss"] > -TTP_MAX_DAILY_DD else "BREACH"
    total_ok = "OK" if m["max_total_dd"] > -TTP_MAX_TOTAL_DD else "BREACH"
    return (
        f"Return={m['ann_return']:+.2%}  Sharpe={m['sharpe']:.2f}  "
        f"MaxTotalDD={m['max_total_dd']:.2%} [{total_ok}]  WorstDay={m['max_daily_loss']:.2%} [{daily_ok}]"
    )


def main():
    print(f"Fetching weekly + daily OHLC GOLD/BTC {START} -> {END} ...")
    weekly = fetch_weekly_gold_btc(START, END)
    daily = fetch_daily_ohlc_gold_btc(START, END)

    print("\n" + "=" * 100)
    print(f"TP/BE/FILTER SWEEP (Limits: {TTP_MAX_DAILY_DD:.0%} Tages-DD / {TTP_MAX_TOTAL_DD:.0%} Gesamt-DD)")
    print("=" * 100)
    for sc in SCENARIOS:
        decision = composite_position(weekly, lookbacks=(4, 8, 12), min_agree=sc["min_agree"]).iloc[WARMUP_WEEKS:]
        sim = simulate_risk_based(
            daily, decision, risk_pct=sc["risk_pct"], atr_mult=sc["atr_mult"],
            tp_r_mult=sc["tp_r_mult"], be_trigger_r=sc["be_trigger_r"], starting_equity=100_000.0,
        )
        m = metrics_from_daily(sim["daily_return"], sim["equity"])
        n_trades = (decision != "cash").sum()
        n_stops = int(sim["stopped_out_today"].sum())
        n_tps = int(sim["tp_hit_today"].sum())
        avg_notional = sim.loc[sim["asset"] != "cash", "notional_fraction"].mean()
        print(f"  {sc['label']:<48}{fmt(m)}")
        print(f"      Trades={n_trades}  Stops={n_stops}  TPs={n_tps}  avg.Positionsgroesse={avg_notional:.1%}")


if __name__ == "__main__":
    main()
