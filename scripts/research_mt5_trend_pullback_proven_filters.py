"""Tests the two REPO-PROVEN filters (not invented for this strategy) on the
MT5 Trend+Pullback bot, at each market's own live timeframe, on the
regime-shifted new IS (2023-01 -> 2024-07) / new OOS (2024-07 -> 2026-08)
window from scripts/research_mt5_trend_pullback_regime_shift.py.

Deliberately reuses EXTERNALLY validated parameters unchanged (quantile=2/3,
alignment window=5 days) rather than re-sweeping them on this strategy's own
tiny new-IS sample - re-tuning would just reintroduce the overfitting risk
that scripts/research_mt5_trend_pullback_tp_sl_be_sweep.py's regime-shift
follow-up already demonstrated. This is the point of using PROVEN filters:
import settings validated on independent, larger data instead of re-fitting.

1. Corwin-Schultz liquidity filter (bond_yield_indicator/friction.py,
   reused via asian_range_breakout/filters.py::apply_gold_liquidity_filter_
   causal - genuinely instrument-agnostic despite the "gold" naming, needs
   only that instrument's own D1 high/low). On the Asian-Range-Breakout
   strategy this passed randomization testing (p=0.000) AND 6/6-year
   expanding walk-forward - the strongest-validated filter candidate in this
   repo, never before applied to another strategy. Applied here per-market
   to each of the 5 markets using each market's OWN friction series.

2. Cross-asset metals-momentum alignment (asian_range_breakout/filters.py::
   attach_silver_alignment concept, adapted for this repo's int direction
   convention (1=long) instead of ASB's string one, and for a long-only
   strategy the "aligned" test collapses to "the confirming asset's own
   5-day change is positive"). Validated direction (Silver confirms Gold)
   applied unchanged; Gold-confirms-Silver and Gold-confirms-Platinum are a
   disclosed, untested-elsewhere extension using the same mechanism.
   NOT applied to CHFJPY/USDJPY - no validated cross-asset partner for FX
   crosses exists elsewhere in this repo, and picking one now would be a
   fresh, unvalidated invention, not a "proven filter".
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.filters import apply_gold_liquidity_filter_causal
from bond_yield_indicator.friction import corwin_schultz_spread
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

LIQUIDITY_QUANTILE = 2 / 3   # unchanged from the validated ASB setting
ALIGNMENT_WINDOW = 5         # unchanged from the validated ASB setting

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]
# market -> D1 key of the asset whose own momentum confirms its trades (None = not tested)
ALIGNMENT_PARTNER = {"GOLD": "SILVER", "SILVER": "GOLD", "PLATINUM": "GOLD", "CHFJPY": None, "USDJPY": None}


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def alignment_filter(trades: pd.DataFrame, partner_close_d1: pd.Series, window: int = ALIGNMENT_WINDOW) -> pd.DataFrame:
    """Long-only adaptation of asian_range_breakout.filters.attach_silver_alignment:
    keep a trade only if the confirming asset's own `window`-day close change,
    as of the entry's calendar date (last value strictly BEFORE entry, no
    lookahead), was positive."""
    if trades.empty:
        return trades
    chg = partner_close_d1.sort_index().pct_change(window)
    entry_dates = trades["entry_time"].dt.tz_localize(None).dt.normalize()
    s_sorted = chg.dropna().sort_index()
    idx = s_sorted.index.searchsorted(entry_dates.to_numpy(), side="left") - 1
    idx_clipped = idx.clip(min=0)
    values = s_sorted.to_numpy()[idx_clipped]
    values = pd.Series(values, index=trades.index, dtype=float)
    values[idx < 0] = np.nan
    out = trades.copy()
    out["partner_chg"] = values
    out = out.dropna(subset=["partner_chg"])
    return out[out["partner_chg"] > 0]


def period_stats(trades: pd.DataFrame, index: pd.DatetimeIndex, start, end) -> dict:
    t = trades[(trades["entry_time"] >= start) & (trades["entry_time"] < end)] if end is not None else trades[trades["entry_time"] >= start]
    idx = index[(index >= start) & (index < end)] if end is not None else index[index >= start]
    return summarize(t, idx)


def main():
    # D1 data for friction + alignment (fetched once per market, reused across both filters)
    d1_close, d1_friction = {}, {}
    for key, tf, label, spread_bps in MARKETS:
        d1 = fetch_timeframe(key, "D1", DATA_START, DATA_END)
        friction = corwin_schultz_spread(d1["High"], d1["Low"])
        if friction.index.tz is not None:
            friction.index = friction.index.tz_localize(None)
        close = d1["Close"]
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        d1_friction[key] = friction
        d1_close[key] = close

    print("=" * 100)
    print("1. CORWIN-SCHULTZ LIQUIDITY FILTER (causal, expanding quantile=2/3, min_periods=250)")
    print("   Externally validated on Asian-Range-Breakout - parameters NOT re-tuned here.")
    print("=" * 100)
    liq_rows = []
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
        trades = simulate_trades(signaled, cfg)

        base_is = period_stats(trades, signaled.index, NEW_IS_START, NEW_SPLIT)
        base_oos = period_stats(trades, signaled.index, NEW_SPLIT, NEW_OOS_END)

        filt_trades = apply_gold_liquidity_filter_causal(trades, d1_friction[key], quantile=LIQUIDITY_QUANTILE)
        filt_is = period_stats(filt_trades, signaled.index, NEW_IS_START, NEW_SPLIT)
        filt_oos = period_stats(filt_trades, signaled.index, NEW_SPLIT, NEW_OOS_END)

        print(f"\n{label}:")
        print(f"  Baseline   IS: {fmt(base_is):<62} OOS: {fmt(base_oos)}")
        print(f"  +Liquidity IS: {fmt(filt_is):<62} OOS: {fmt(filt_oos)}")
        liq_rows.append({"market": label, "base_oos": base_oos, "filt_oos": filt_oos})

    print("\n" + "=" * 100)
    print(f"2. CROSS-ASSET METALS-ALIGNMENT FILTER ({ALIGNMENT_WINDOW}-day partner momentum > 0)")
    print("   Silver-confirms-Gold direction externally validated on ASB; Gold-confirms-Silver/Platinum")
    print("   are a disclosed, untested-elsewhere mirror extension using the identical mechanism.")
    print("=" * 100)
    align_rows = []
    for key, tf, label, spread_bps in MARKETS:
        partner = ALIGNMENT_PARTNER[key]
        if partner is None:
            print(f"\n{label}: skipped (no validated cross-asset partner)")
            continue
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
        trades = simulate_trades(signaled, cfg)

        base_is = period_stats(trades, signaled.index, NEW_IS_START, NEW_SPLIT)
        base_oos = period_stats(trades, signaled.index, NEW_SPLIT, NEW_OOS_END)

        filt_trades = alignment_filter(trades, d1_close[partner])
        filt_is = period_stats(filt_trades, signaled.index, NEW_IS_START, NEW_SPLIT)
        filt_oos = period_stats(filt_trades, signaled.index, NEW_SPLIT, NEW_OOS_END)

        print(f"\n{label} (confirmed by {partner}):")
        print(f"  Baseline    IS: {fmt(base_is):<62} OOS: {fmt(base_oos)}")
        print(f"  +Alignment  IS: {fmt(filt_is):<62} OOS: {fmt(filt_oos)}")
        align_rows.append({"market": label, "partner": partner, "base_oos": base_oos, "filt_oos": filt_oos})

    print("\n" + "=" * 100)
    print("3. SUMMARY")
    print("=" * 100)
    print("\nLiquidity filter, OOS PF change:")
    for r in liq_rows:
        arrow = "UP" if r["filt_oos"]["profit_factor"] > r["base_oos"]["profit_factor"] else "DOWN"
        print(f"  {r['market']:<8} PF {r['base_oos']['profit_factor']:.3f} -> {r['filt_oos']['profit_factor']:.3f}  ({arrow})")
    print("\nAlignment filter, OOS PF change:")
    for r in align_rows:
        arrow = "UP" if r["filt_oos"]["profit_factor"] > r["base_oos"]["profit_factor"] else "DOWN"
        print(f"  {r['market']:<8} PF {r['base_oos']['profit_factor']:.3f} -> {r['filt_oos']['profit_factor']:.3f}  ({arrow})")


if __name__ == "__main__":
    main()
