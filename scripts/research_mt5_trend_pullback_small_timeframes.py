"""Extends scripts/research_mt5_trend_pullback_regime_shift.py's timeframe
comparison (step 1) with intraday timeframes below H1: M5, M15, M30 (native
Dukascopy intervals) and M3 (Dukascopy has no native M3 - built by resampling
M1 bars, OHLC-correct: open=first, high=max, low=min, close=last,
volume=sum).

Same bot config (EMA150/RSI14x35/ATR14x2.0/RR2.0, no filter) and same
regime-shifted new IS (2023-01-01 -> 2024-07-01) / new OOS (2024-07-01 ->
2026-08-01) split as the parent script - this is purely an extra timeframe
row per market, not a new methodology.

Caveat carried over unchanged: EMA(150)/RSI(14)/ATR(14) are bar-count
parameters, so "150 bars" means a dramatically shorter real-world lookback
at M3/M5 than at H1 (150 H1 bars = ~6.25 days; 150 M5 bars = 12.5 hours) -
this tests "what if the bot pointed its exact own logic at a faster
timeframe", not "what if the bot's lookback windows were recalibrated for
that timeframe" (a different, not-asked-for question).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

# Only the regime-shifted window is needed (plus a small warmup buffer) -
# fetching M1/M5 data back to 2016 would be enormous and pointless here.
FETCH_START = "2022-11-01"
FETCH_END = "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

MARKETS = [
    ("GOLD", "XAUUSD", 10.0),
    ("SILVER", "XAGUSD", 10.0),
    ("PLATINUM", "XPTUSD", 10.0),
    ("CHFJPY", "CHFJPY", 3.0),
    ("USDJPY", "USDJPY", 1.5),
]
NATIVE_TFS = ["M5", "M15", "M30"]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>5}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def resample_m1_to_m3(df_m1: pd.DataFrame) -> pd.DataFrame:
    out = df_m1.resample("3min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna(subset=["open", "high", "low", "close"])


def backtest(df: pd.DataFrame, spread_bps: float) -> tuple[dict, dict]:
    signaled = run_pipeline(df)
    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
    trades = simulate_trades(signaled, cfg)
    is_t = trades[(trades["entry_time"] >= NEW_IS_START) & (trades["entry_time"] < NEW_SPLIT)]
    is_idx = signaled.index[(signaled.index >= NEW_IS_START) & (signaled.index < NEW_SPLIT)]
    oos_t = trades[trades["entry_time"] >= NEW_SPLIT]
    oos_idx = signaled.index[signaled.index >= NEW_SPLIT]
    return summarize(is_t, is_idx), summarize(oos_t, oos_idx)


def main():
    print("=" * 100)
    print("SMALL-TIMEFRAME EXTENSION (M3/M5/M15/M30) -- bot default config, new IS/OOS window")
    print("=" * 100)

    rows = []
    for key, label, spread_bps in MARKETS:
        print(f"\n{label}:")
        for tf in NATIVE_TFS:
            df = fetch_timeframe(key, tf, FETCH_START, FETCH_END)
            df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
            s_is, s_oos = backtest(df, spread_bps)
            print(f"  {tf:<4} IS: {fmt(s_is):<62} OOS: {fmt(s_oos)}")
            rows.append({"market": label, "tf": tf, "is": s_is, "oos": s_oos})

        print(f"  Fetching M1 for M3 resample ({FETCH_START} -> {FETCH_END}) ...")
        df_m1 = fetch_timeframe(key, "M1", FETCH_START, FETCH_END)
        df_m1 = df_m1.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        print(f"    {len(df_m1)} M1 bars -> resampling to M3 ...")
        df_m3 = resample_m1_to_m3(df_m1)
        s_is, s_oos = backtest(df_m3, spread_bps)
        print(f"  M3   IS: {fmt(s_is):<62} OOS: {fmt(s_oos)}")
        rows.append({"market": label, "tf": "M3", "is": s_is, "oos": s_oos})

    out_rows = []
    for r in rows:
        out_rows.append({
            "market": r["market"], "tf": r["tf"],
            "n_is": r["is"]["n_trades"], "wr_is": r["is"]["win_rate"], "pf_is": r["is"]["profit_factor"], "sharpe_is": r["is"]["sharpe"],
            "n_oos": r["oos"]["n_trades"], "wr_oos": r["oos"]["win_rate"], "pf_oos": r["oos"]["profit_factor"], "sharpe_oos": r["oos"]["sharpe"],
            "cagr_oos": r["oos"]["cagr"], "maxdd_oos": r["oos"]["max_drawdown"],
        })
    out_dir = Path(__file__).resolve().parents[1] / "mt5_trend_pullback" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "small_timeframes.csv"
    pd.DataFrame(out_rows).to_csv(out_path, index=False)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
