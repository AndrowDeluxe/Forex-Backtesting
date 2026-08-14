"""Tests the Execution-Overlay entry-timing adaptation
(mt5_trend_pullback/execution_overlay.py) on the new STANDARD 4-market
portfolio (Platinum dropped, Gold-confirms-Silver alignment filter on
Silver - see scripts/research_mt5_trend_pullback_market_dropout.py), on the
regime-shifted new IS (2023-01->2024-07) / new OOS (2024-07->2026-08)
window.

Prior-art warning this test is deliberately checking against (see
execution_overlay/ SPY H1 finding): the overlay flipped from neutral to
actively harmful once bars got as coarse as H1, because waiting for a
counter-bar costs a much larger fraction of a short holding period at H1
than at 5-min resolution. This strategy trades H1 (Gold/Silver) and H4
(CHFJPY/USDJPY) - exactly the coarse-resolution regime that prior test
flagged as risky, so a negative result here would not be surprising and is
reported either way.

`max_wait_bars=5` is a disclosed, NOT validated-elsewhere adaptation choice
(the ASB version's overlay has a natural "session end" cutoff this
always-on strategy has no equivalent of) - a small sensitivity check (3/5/10
bars) is included to see how much the result depends on that choice.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.execution_overlay import simulate_trades_overlay
from mt5_trend_pullback.filters import alignment_filter
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

# The new standard portfolio (Platinum dropped)
MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]
WAIT_BARS_CANDIDATES = [3, 5, 10]


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


def slice_period(t: pd.DataFrame, idx: pd.DatetimeIndex, start, end) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    tt = t[(t["entry_time"] >= start) & (t["entry_time"] < end)] if end is not None else t[t["entry_time"] >= start]
    ii = idx[(idx >= start) & (idx < end)] if end is not None else idx[idx >= start]
    return tt, ii


def main():
    d1_close = {}
    signaled_by_market = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled_by_market[label] = (run_pipeline(df), spread_bps)

        d1 = fetch_timeframe(key, "D1", DATA_START, DATA_END)
        close = d1["Close"]
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        d1_close[key] = close

    print("=" * 100)
    print("1. BASELINE vs. EXECUTION-OVERLAY (max_wait_bars=5), per market, new OOS")
    print("=" * 100)
    base_oos_tbm, overlay_oos_tbm = {}, {}
    base_oos_idx, overlay_oos_idx = {}, {}
    for label, (signaled, spread_bps) in signaled_by_market.items():
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
        base_trades = simulate_trades(signaled, cfg)
        overlay_trades = simulate_trades_overlay(signaled, cfg, max_wait_bars=5)

        if label == "XAGUSD":
            base_trades = alignment_filter(base_trades, d1_close["GOLD"])
            overlay_trades = alignment_filter(overlay_trades, d1_close["GOLD"])

        base_oos_t, base_oos_i = slice_period(base_trades, signaled.index, NEW_SPLIT, NEW_OOS_END)
        overlay_oos_t, overlay_oos_i = slice_period(overlay_trades, signaled.index, NEW_SPLIT, NEW_OOS_END)
        base_oos_tbm[label], base_oos_idx[label] = base_oos_t, base_oos_i
        overlay_oos_tbm[label], overlay_oos_idx[label] = overlay_oos_t, overlay_oos_i

        s_base, s_overlay = summarize(base_oos_t, base_oos_i), summarize(overlay_oos_t, overlay_oos_i)
        print(f"\n{label}:")
        print(f"  Baseline (fill@next open) : {fmt(s_base)}")
        print(f"  Overlay  (wait+fill@close): {fmt(s_overlay)}")
        if not overlay_trades.empty:
            print(f"    median wait_bars={overlay_trades['wait_bars'].median():.0f}, "
                  f"signals skipped (no counter-bar within 5 bars): see step 2")

    print("\n" + "=" * 100)
    print("2. POOLED PORTFOLIO (4 markets), new OOS")
    print("=" * 100)
    s_base_pooled = combined(base_oos_tbm, base_oos_idx)
    s_overlay_pooled = combined(overlay_oos_tbm, overlay_oos_idx)
    print(f"  Baseline: {fmt(s_base_pooled)}")
    print(f"  Overlay : {fmt(s_overlay_pooled)}")

    print("\n" + "=" * 100)
    print("3. SENSITIVITY TO max_wait_bars (pooled portfolio, new OOS)")
    print("=" * 100)
    for wb in WAIT_BARS_CANDIDATES:
        tbm, idxm = {}, {}
        for label, (signaled, spread_bps) in signaled_by_market.items():
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
            overlay_trades = simulate_trades_overlay(signaled, cfg, max_wait_bars=wb)
            if label == "XAGUSD":
                overlay_trades = alignment_filter(overlay_trades, d1_close["GOLD"])
            t, i = slice_period(overlay_trades, signaled.index, NEW_SPLIT, NEW_OOS_END)
            tbm[label], idxm[label] = t, i
        s = combined(tbm, idxm)
        print(f"  max_wait_bars={wb:>2}  {fmt(s)}")


if __name__ == "__main__":
    main()
