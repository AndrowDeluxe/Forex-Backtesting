"""Tests the MT5 Trend+Pullback bot's exact signal logic (unchanged
EMA150/RSI14x35/ATR14x2.0/RR2.0, no filters) on three FX majors it doesn't
currently trade: EURUSD, GBPUSD, USDCAD - "how do other majors react to the
system?" Same regime-shifted new IS (2023-01->2024-07) / new OOS
(2024-07->2026-08) window as every other pass in this series.

Timeframe: H4, matching the live bot's own FX convention (CHFJPY/USDJPY
both trade H4, not H1) - H1 was tested for CHFJPY/USDJPY in scripts/
research_mt5_trend_pullback_regime_shift.py's timeframe comparison and
found weaker there, so H4 is the natural default for these three too,
not a fresh choice.

Spread assumptions (round-trip, disclosed estimates, no historical spread
feed in this repo): EURUSD 1.0bp, GBPUSD 1.5bp, USDCAD 1.5bp - EURUSD is
the single deepest FX pair traded (tighter than USDJPY's 1.5bp), GBPUSD/
USDCAD assumed comparable to USDJPY.
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

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

CANDIDATE_MARKETS = [
    ("EURUSD", "H4", "EURUSD", 1.0),
    ("GBPUSD", "H4", "GBPUSD", 1.5),
    ("USDCAD", "H4", "USDCAD", 1.5),
]
# existing standard portfolio, for a combined-with-candidates comparison
EXISTING_STANDARD = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def combined(trades_by_market: dict, index_by_market: dict) -> dict:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    if not starts:
        return summarize(combined_trades, pd.DatetimeIndex([]))
    full_index = pd.date_range(min(starts), max(ends), freq="D")
    return summarize(combined_trades, full_index)


def backtest(key: str, tf: str, spread_bps: float):
    df = fetch_timeframe(key, tf, DATA_START, DATA_END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    signaled = run_pipeline(df)
    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
    trades = simulate_trades(signaled, cfg)
    is_t = trades[(trades["entry_time"] >= NEW_IS_START) & (trades["entry_time"] < NEW_SPLIT)]
    is_idx = signaled.index[(signaled.index >= NEW_IS_START) & (signaled.index < NEW_SPLIT)]
    oos_t = trades[trades["entry_time"] >= NEW_SPLIT]
    oos_idx = signaled.index[signaled.index >= NEW_SPLIT]
    return trades, signaled.index, summarize(is_t, is_idx), summarize(oos_t, oos_idx), oos_t, oos_idx


def main():
    print("=" * 100)
    print("1. FX MAJORS -- bot default config, H4, new IS/OOS window")
    print("=" * 100)
    candidate_oos_tbm, candidate_oos_idx = {}, {}
    for key, tf, label, spread_bps in CANDIDATE_MARKETS:
        _, _, s_is, s_oos, oos_t, oos_idx = backtest(key, tf, spread_bps)
        candidate_oos_tbm[label], candidate_oos_idx[label] = oos_t, oos_idx
        print(f"\n{label} ({tf}, spread={spread_bps}bp):")
        print(f"  IS : {fmt(s_is)}")
        print(f"  OOS: {fmt(s_oos)}")

    print("\n" + "=" * 100)
    print("2. POOLED (3 new FX majors alone)")
    print("=" * 100)
    print(f"  {fmt(combined(candidate_oos_tbm, candidate_oos_idx))}")

    print("\n" + "=" * 100)
    print("3. EXISTING STANDARD PORTFOLIO (Gold/Silver/CHFJPY/USDJPY) -- for reference")
    print("=" * 100)
    existing_oos_tbm, existing_oos_idx = {}, {}
    from mt5_trend_pullback.filters import alignment_filter
    gold_d1 = fetch_timeframe("GOLD", "D1", DATA_START, DATA_END)["Close"]
    if gold_d1.index.tz is not None:
        gold_d1.index = gold_d1.index.tz_localize(None)
    for key, tf, label, spread_bps in EXISTING_STANDARD:
        trades, idx, s_is, s_oos, oos_t, oos_idx = backtest(key, tf, spread_bps)
        if label == "XAGUSD":
            oos_t = alignment_filter(oos_t, gold_d1)
        existing_oos_tbm[label], existing_oos_idx[label] = oos_t, oos_idx
    s_existing = combined(existing_oos_tbm, existing_oos_idx)
    print(f"  {fmt(s_existing)}")

    print("\n" + "=" * 100)
    print("4. COMBINED: existing standard (4) + each FX major added individually")
    print("=" * 100)
    for key, tf, label, spread_bps in CANDIDATE_MARKETS:
        tbm = dict(existing_oos_tbm)
        idxm = dict(existing_oos_idx)
        tbm[label] = candidate_oos_tbm[label]
        idxm[label] = candidate_oos_idx[label]
        s = combined(tbm, idxm)
        arrow = "UP" if s["sharpe"] > s_existing["sharpe"] else "DOWN"
        print(f"  + {label:<8} {fmt(s)}  (Sharpe {arrow} vs standard-4 {s_existing['sharpe']:.2f})")

    print("\n" + "=" * 100)
    print("5. ALL 7 COMBINED (standard 4 + all 3 new majors)")
    print("=" * 100)
    tbm_all = {**existing_oos_tbm, **candidate_oos_tbm}
    idxm_all = {**existing_oos_idx, **candidate_oos_idx}
    s_all = combined(tbm_all, idxm_all)
    print(f"  {fmt(s_all)}")


if __name__ == "__main__":
    main()
