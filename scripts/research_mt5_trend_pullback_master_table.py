"""Builds the final master table requested by the user: bot DEFAULT config
(no filter, EMA150/RSI14x35/ATR14x2.0/RR2.0 - the live bot exactly as
configured today) at each market's own LIVE timeframe (H1 metals, H4 FX),
evaluated on the regime-shifted new OOS window (2024-07-01 -> 2026-08-01,
per scripts/research_mt5_trend_pullback_regime_shift.py), at four risk
levels (0.5% / 1.0% / 1.5% / 2.0%) on a $100,000 account.

Why the DEFAULT config and not the "optimized" one from the regime-shift
script: that sweep's chosen filter/TP-SL/BE combo overfit badly (new-IS
Sharpe 2.46 collapsed to new-OOS Sharpe 0.11, WORSE than doing nothing) - see
that script's step 3/4 output. The untouched bot default (new-OOS Sharpe
0.78, PF 1.37) is the more trustworthy number and is what's used here.

Writes mt5_trend_pullback/results/master_table.csv (long format: one row per
market x risk_pct, plus portfolio-level rows) for the HTML artifact/summary.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.account_simulation import account_stats, simulate_account
from mt5_trend_pullback.pipeline import (
    ATR_LEN, ATR_STOP_MULT, RR_RATIO, RSI_LEN, RSI_OVERSOLD, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]

STARTING_EQUITY = 100_000.0
RISK_LEVELS = [0.005, 0.01, 0.015, 0.02]
MAX_CONCURRENT = 3


def main():
    trades_by_market_oos = {}
    trades_by_market_is = {}
    rows = []
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)

        is_t = trades[(trades["entry_time"] >= NEW_IS_START) & (trades["entry_time"] < NEW_SPLIT)]
        is_idx = signaled.index[(signaled.index >= NEW_IS_START) & (signaled.index < NEW_SPLIT)]
        oos_t = trades[trades["entry_time"] >= NEW_SPLIT]
        oos_idx = signaled.index[signaled.index >= NEW_SPLIT]

        trades_by_market_oos[label] = oos_t
        trades_by_market_is[label] = is_t

        s_is, s_oos = summarize(is_t, is_idx), summarize(oos_t, oos_idx)

        for risk_pct in RISK_LEVELS:
            sim = simulate_account({label: oos_t}, starting_equity=STARTING_EQUITY, risk_pct=risk_pct, max_concurrent=1)
            acc = account_stats(sim, starting_equity=STARTING_EQUITY)
            rows.append({
                "scope": "per_market", "market": label, "timeframe": tf, "spread_bps": spread_bps,
                "risk_pct": risk_pct,
                "trend_ema": TREND_LEN, "rsi_len": RSI_LEN, "rsi_oversold": RSI_OVERSOLD, "atr_len": ATR_LEN,
                "stop_atr_mult": ATR_STOP_MULT, "rr_ratio": RR_RATIO,
                "new_is_start": NEW_IS_START.date().isoformat(), "new_split": NEW_SPLIT.date().isoformat(), "new_oos_end": NEW_OOS_END.date().isoformat(),
                "n_is": s_is["n_trades"], "wr_is": s_is["win_rate"], "pf_is": s_is["profit_factor"], "sharpe_is": s_is["sharpe"],
                "n_oos": s_oos["n_trades"], "wr_oos": s_oos["win_rate"], "pf_oos": s_oos["profit_factor"],
                "sharpe_oos": s_oos["sharpe"], "calmar_oos": s_oos["calmar"], "cagr_oos": s_oos["cagr"], "maxdd_pct_oos": s_oos["max_drawdown"],
                "avg_hold_bars_oos": s_oos["avg_hold_bars"],
                "final_equity": acc["final_equity"], "total_return": acc["total_return"],
                "maxdd_usd": acc["max_drawdown_usd"], "avg_win_usd": acc["avg_win_usd"], "avg_loss_usd": acc["avg_loss_usd"],
                "n_taken": acc["n_trades"], "n_skipped": acc["n_skipped"],
            })

    # portfolio-level (all 5 markets, max 3 concurrent -- the bot's real constraint)
    for risk_pct in RISK_LEVELS:
        sim = simulate_account(trades_by_market_oos, starting_equity=STARTING_EQUITY, risk_pct=risk_pct, max_concurrent=MAX_CONCURRENT)
        acc = account_stats(sim, starting_equity=STARTING_EQUITY)
        rows.append({
            "scope": "portfolio", "market": "ALLE 5 MAERKTE", "timeframe": "gemischt", "spread_bps": None,
            "risk_pct": risk_pct,
            "trend_ema": TREND_LEN, "rsi_len": RSI_LEN, "rsi_oversold": RSI_OVERSOLD, "atr_len": ATR_LEN,
            "stop_atr_mult": ATR_STOP_MULT, "rr_ratio": RR_RATIO,
            "new_is_start": NEW_IS_START.date().isoformat(), "new_split": NEW_SPLIT.date().isoformat(), "new_oos_end": NEW_OOS_END.date().isoformat(),
            "n_is": None, "wr_is": None, "pf_is": None, "sharpe_is": None,
            "n_oos": None, "wr_oos": None, "pf_oos": None, "sharpe_oos": None, "calmar_oos": None, "cagr_oos": None, "maxdd_pct_oos": None,
            "avg_hold_bars_oos": None,
            "final_equity": acc["final_equity"], "total_return": acc["total_return"],
            "maxdd_usd": acc["max_drawdown_usd"], "avg_win_usd": acc["avg_win_usd"], "avg_loss_usd": acc["avg_loss_usd"],
            "n_taken": acc["n_trades"], "n_skipped": acc["n_skipped"],
        })

    out_df = pd.DataFrame(rows)
    out_dir = Path(__file__).resolve().parents[1] / "mt5_trend_pullback" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "master_table.csv"
    out_df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(out_df)} rows)")
    with pd.option_context("display.float_format", lambda x: f"{x:.3f}"):
        print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
