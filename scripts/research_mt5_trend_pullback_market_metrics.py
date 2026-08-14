"""Detailed per-market metrics (Sharpe, Calmar, CAGR, MaxDD, PF, WR, avg
hold) for the MT5 Trend+Pullback bot replication, Full/IS/OOS, both without
and with the ADX>=25 regime filter from
scripts/research_mt5_trend_pullback_adx_filter.py. Follow-up to that script
and scripts/research_mt5_trend_pullback.py, which only printed a compact
one-line summary per market - this expands that into the full metric set."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
CHOSEN_ADX_MIN = 25.0

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]


def main():
    data = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = (df, spread_bps)

    for variant_name, adx_min in [("BASELINE (kein Filter)", None), (f"ADX>={CHOSEN_ADX_MIN:.0f}-FILTER", CHOSEN_ADX_MIN)]:
        print("\n" + "=" * 100)
        print(variant_name)
        print("=" * 100)
        rows = []
        for label, (df, spread_bps) in data.items():
            signaled = run_pipeline(df, adx_min=adx_min)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades = simulate_trades(signaled, cfg)
            periods = {
                "Full": (trades, signaled.index),
                "IS": (trades[trades["entry_time"] < SPLIT], signaled.index[signaled.index < SPLIT]),
                "OOS": (trades[trades["entry_time"] >= SPLIT], signaled.index[signaled.index >= SPLIT]),
            }
            for period_name, (t, sub_idx) in periods.items():
                s = summarize(t, sub_idx)
                rows.append({
                    "Markt": label, "Periode": period_name, "n": s["n_trades"],
                    "Trefferquote": s["win_rate"], "Profit-Faktor": s["profit_factor"],
                    "Sharpe": s["sharpe"], "Calmar": s["calmar"], "CAGR": s["cagr"],
                    "MaxDD": s["max_drawdown"], "Oe.Hold(bars)": s["avg_hold_bars"],
                    "Oe.Return/Trade": s["avg_return_pct"],
                })
        df_out = pd.DataFrame(rows)
        with pd.option_context("display.float_format", lambda x: f"{x:.3f}"):
            print(df_out.to_string(index=False))


if __name__ == "__main__":
    main()
