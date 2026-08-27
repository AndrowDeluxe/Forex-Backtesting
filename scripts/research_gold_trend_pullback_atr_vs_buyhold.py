"""Follow-up to research_gold_trend_pullback_atr_regime_filter.py: that
script's OOS (2023-2026) result for the ADX>=35-filtered strategy looked
decent (PF=1.355, Sharpe=0.78) after a filter that was NEVER profitable
in-sample - suspicious, since 2023-2026 was a strong secular Gold bull run
and a long-only strategy can look good in a rally almost regardless of
entry precision (market beta, not timing alpha).

This script settles that directly: same OOS window, same Gold instrument,
simple buy-and-hold (no timing at all) vs. the filtered strategy, both
through strategy.metrics so the numbers are apples-to-apples.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from gold_trend_pullback_atr.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2016-01-01", "2026-08-01"  # full fetch - trend EMA needs pre-OOS warmup history
SPLIT = pd.Timestamp("2023-01-01", tz="America/New_York")
SPREAD_BPS = 10.0

FIXED_TREND_EMA, FIXED_FAST_EMA = 100, 10
FIXED_STOP_ATR, FIXED_TP_R = 3.0, 3.0
CHOSEN_ADX_MIN = 35.0  # selected on IS only in the prior script


def fmt(label: str, sharpe: float, cagr_: float, mdd: float) -> str:
    return f"  {label:<28} Sharpe={sharpe:>6.2f}  CAGR={cagr_:>+7.1%}  MaxDD={mdd:>7.1%}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    oos_df = df[df.index >= SPLIT]
    print(f"OOS window: {oos_df.index.min()} -> {oos_df.index.max()}  ({len(oos_df)} M15 bars)")

    # --- Buy & hold: daily close-to-close, one-time entry cost only ---
    daily_close = oos_df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4  # one-time entry half-spread, no further trading costs
    bh_sharpe = annualized_sharpe(daily_ret)
    bh_cagr = cagr(daily_ret)
    bh_mdd = max_drawdown(daily_ret)
    total_return = (1 + daily_ret).prod() - 1

    # --- Filtered strategy, OOS only (re-derived, same as regime_filter script) ---
    signaled = run_pipeline(df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA, adx_min=CHOSEN_ADX_MIN)
    oos_mask = signaled.index >= SPLIT
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False, take_profit_r=FIXED_TP_R)
    trades = simulate_trades(signaled[oos_mask], cfg)
    strat_stats = summarize(trades, signaled[oos_mask].index)

    print("\n" + "=" * 78)
    print("OOS (2023-2026) COMPARISON: strategy vs. simple buy-and-hold")
    print("=" * 78)
    print(fmt("Buy & hold Gold:", bh_sharpe, bh_cagr, bh_mdd))
    print(f"  {'':28} total return over window: {total_return:+.1%}")
    print(fmt("ADX>=35 filtered strategy:", strat_stats["sharpe"], strat_stats["cagr"], strat_stats["max_drawdown"]))
    print(f"  {'':28} n_trades={strat_stats['n_trades']}, time in market: only while a position is open (vs. 100% for buy&hold)")

    print("\nInterpretation:")
    if strat_stats["sharpe"] > bh_sharpe and strat_stats["cagr"] > 0:
        print("  Strategy beats buy-and-hold on both Sharpe and CAGR in this window - some")
        print("  evidence of genuine value beyond just being long Gold, though still a single")
        print("  OOS window (one bull market), not a robust multi-regime validation.")
    else:
        print("  Buy-and-hold matches or beats the strategy on a risk-adjusted basis here -")
        print("  consistent with the OOS 'edge' being market beta (long Gold in a rally),")
        print("  not genuine timing value from the entry/filter logic.")


if __name__ == "__main__":
    main()
