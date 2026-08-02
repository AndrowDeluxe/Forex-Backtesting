"""MFE/MAE analysis and take-profit sweep for the ORB long-only + ADX>=25 +
per-asset weekday-filter strategy (Nasdaq: no Thursday, SP500: no Monday).

Question: does the current "ride to session-end" exit leave real upside on
the table, or does it already capture most of what's available (consistent
with the loss-profile finding that risk comes from trades that lose from
the start, not winners giving back gains)?

1. Descriptive: for winners vs. losers, mean/median Maximum Favourable
   Excursion (MFE, in R-multiples and bps) and Maximum Adverse Excursion
   (MAE) - tracked unconditionally by strategy/backtest.py::simulate_trades
   now (mfe_r/mae_r columns). "Capture ratio" for winners = realized return
   / MFE - how much of the available upside the session-end exit actually
   captured.
2. An actual take_profit_r sweep (new BacktestConfig field) - not just
   descriptive stats, a real backtest of adding a fixed R-multiple target,
   full-period and Out-of-Sample (2021-2026).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
STOP_MULT = 2.0
ASSET_CONFIG = {"NASDAQ": "Thursday", "SP500": "Monday"}


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def mfe_mae_analysis(trades: pd.DataFrame, name: str):
    print(f"\n{'=' * 15} {name}: MFE/MAE-Analyse (Full-Period) {'=' * 15}")
    if trades.empty:
        print("  Keine Trades.")
        return

    t = trades.copy()
    t["mfe_bps"] = t["mfe_r"] * (STOP_MULT * t["atr_at_entry"] / t["entry_price"]) * 1e4
    t["realized_bps"] = t["return_pct"] * 1e4
    wins = t["return_pct"] > 0

    for label, group in [("Gewinner", t[wins]), ("Verlierer", t[~wins])]:
        if group.empty:
            print(f"\n{label}: keine Trades")
            continue
        print(f"\n{label} (n={len(group)}):")
        print(f"  MFE (R-Multiple):    mean={group['mfe_r'].mean():.2f}, median={group['mfe_r'].median():.2f}")
        print(f"  MAE (R-Multiple):    mean={group['mae_r'].mean():.2f}, median={group['mae_r'].median():.2f}")
        print(f"  MFE (bps):           mean={group['mfe_bps'].mean():.1f}, median={group['mfe_bps'].median():.1f}")
        print(f"  Realisiert (bps):    mean={group['realized_bps'].mean():.1f}, median={group['realized_bps'].median():.1f}")
        if label == "Gewinner":
            capture = group["realized_bps"] / group["mfe_bps"].replace(0, pd.NA)
            print(f"  Capture-Ratio (realisiert/MFE): mean={capture.mean():.1%}, median={capture.median():.1%}")

    frac_losers_with_upside = ((t.loc[~wins, "mfe_r"]) >= 1.0).mean() if (~wins).sum() > 0 else float("nan")
    print(f"\nAnteil Verlierer, die zwischenzeitlich >=1R im Plus standen: {frac_losers_with_upside:.1%}")


def tp_sweep(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name}: Take-Profit-Sweep {'=' * 15}")
    exclude_weekday = ASSET_CONFIG[name]
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=exclude_weekday)
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]

    for tp_r in [None, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False, take_profit_r=tp_r)
        trades = simulate_trades(signaled, cfg)
        oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades

        full_s = summarize(trades, signaled.index)
        oos_s = summarize(oos_trades, oos_signaled.index) if not oos_trades.empty else None
        exit_mix = trades["exit_reason"].value_counts().to_dict() if not trades.empty else {}

        label = "kein TP" if tp_r is None else f"TP={tp_r}R"
        print(f"\n{label}: exit_mix={exit_mix}")
        print(f"  Full: n={full_s['n_trades']}, sharpe={full_s['sharpe']:.2f}, pf={full_s['profit_factor']:.2f}, avg_bps={full_s['avg_return_pct']*1e4:.2f}, max_dd={full_s['max_drawdown']:.1%}")
        if oos_s:
            print(f"  OOS:  n={oos_s['n_trades']}, sharpe={oos_s['sharpe']:.2f}, pf={oos_s['profit_factor']:.2f}, avg_bps={oos_s['avg_return_pct']*1e4:.2f}, max_dd={oos_s['max_drawdown']:.1%}")


def main():
    print("Loading NASDAQ M15...")
    nasdaq = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))
    signaled_nasdaq = run_orb_pipeline(nasdaq, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday="Thursday")
    trades_nasdaq = simulate_trades(signaled_nasdaq, BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False))
    mfe_mae_analysis(trades_nasdaq, "NASDAQ")
    tp_sweep("NASDAQ", nasdaq)

    print("\nLoading SP500 M15...")
    sp500 = _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END))
    signaled_sp500 = run_orb_pipeline(sp500, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday="Monday")
    trades_sp500 = simulate_trades(signaled_sp500, BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False))
    mfe_mae_analysis(trades_sp500, "SP500")
    tp_sweep("SP500", sp500)


if __name__ == "__main__":
    main()
