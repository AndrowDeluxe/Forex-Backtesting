"""Combine the two independently-validated gold SMC strategies from this
session's research into one portfolio (chat 2026-08-19 request):

  - Continuation (gold_smc_htf_ltf/continuation.py): adx_di trend filter on
    M15, entry_variant="direct", tp_mode="h4_level", min_target_distance_atr
    =0.5, stop_atr_mult=0.5, be=None, htf_valid_bars=24 (M5 entries).
    Winning config from research_gold_smc_continuation_exit_sweep.py:
    OOS Sharpe=1.34, PF=2.412.
  - Reversal cascade (gold_smc_htf_ltf/reversal_cascade.py): require_
    ema_reject=True, h4_confirm_bars=30, h1_valid_bars=24 (M15 entries).
    Winning config from research_gold_smc_reversal_cascade[_structural].py:
    stop_atr_mult=0.5, be=0.5, tp_mode=h4_level, OOS Sharpe=0.78, PF=1.485.

No new parameters are fit here - both configs are taken as-is from their
own already-validated OOS runs. Only the PORTFOLIO WEIGHT (how much
capital each strategy gets) is a new choice, tested at a few fixed splits
rather than optimized (optimizing it on the same OOS window it's tested
on would be circular).

Each strategy's own simulate_trades() assumes one full-notional position
at a time WITHIN that strategy (see strategy/backtest.py docstring). To
combine, each strategy's trades are converted to a daily return series
(trades_to_daily_returns - same-day trades compound, no-trade days are
0.0) over a shared OOS calendar index, then blended by capital weight:
combined_daily = w_cont * daily_cont + w_rev * daily_rev.
This assumes independent margin/capital per strategy (standard "sleeve"
portfolio construction), not that they can never have a position open at
the same time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0


def fmt_daily(daily: pd.Series, n_trades: int | None = None) -> str:
    sh, cg, mdd = annualized_sharpe(daily), cagr(daily), max_drawdown(daily)
    extra = f"  n_trades={n_trades}" if n_trades is not None else ""
    return f"Sharpe={sh:.2f}  CAGR={cg:+.1%}  MaxDD={mdd:.1%}{extra}"


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    print("\n--- Continuation: recomputing winning config ---")
    cont_signaled = run_continuation(
        h4, h1, m5, trend_df=m15, trend_indicator="adx_di",
        htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5,
    )
    cont_cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)
    cont_oos_sig = cont_signaled[cont_signaled.index >= SPLIT]
    cont_trades = simulate_trades(cont_oos_sig, cont_cfg)
    cont_stats = summarize(cont_trades, cont_oos_sig.index)
    print(f"  Continuation OOS: n={cont_stats['n_trades']} WR={cont_stats['win_rate']:.1%} PF={cont_stats['profit_factor']:.3f} Sharpe={cont_stats['sharpe']:.2f}")

    print("\n--- Reversal cascade: recomputing winning config ---")
    rev_signaled = run_reversal(h4, h1, m15, require_ema_reject=True, h4_confirm_bars=30, h1_valid_bars=24)
    rev_cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=0.5, max_hold_bars=24 * 4)
    rev_oos_sig = rev_signaled[rev_signaled.index >= SPLIT]
    rev_trades = simulate_trades(rev_oos_sig, rev_cfg)
    rev_stats = summarize(rev_trades, rev_oos_sig.index)
    print(f"  Reversal OOS:     n={rev_stats['n_trades']} WR={rev_stats['win_rate']:.1%} PF={rev_stats['profit_factor']:.3f} Sharpe={rev_stats['sharpe']:.2f}")

    common_days = pd.date_range(SPLIT.normalize(), pd.Timestamp(END, tz="America/New_York").normalize(), freq="D")
    common_index = pd.DatetimeIndex([common_days.min(), common_days.max()])
    daily_cont = trades_to_daily_returns(cont_trades, common_index)
    daily_rev = trades_to_daily_returns(rev_trades, common_index)
    daily_cont, daily_rev = daily_cont.align(daily_rev, join="outer", fill_value=0.0)

    print("\n" + "=" * 78)
    print("OVERLAP DIAGNOSTIC")
    print("=" * 78)
    both_active = (daily_cont != 0) & (daily_rev != 0)
    print(f"  Days with a Continuation trade: {(daily_cont != 0).sum()}")
    print(f"  Days with a Reversal trade:     {(daily_rev != 0).sum()}")
    print(f"  Days with BOTH:                 {both_active.sum()}")
    opposing = both_active & (((daily_cont > 0) & (daily_rev < 0)) | ((daily_cont < 0) & (daily_rev > 0)))
    print(f"  Days both active AND opposite-signed P&L: {opposing.sum()}")
    corr = daily_cont.corr(daily_rev)
    print(f"  Correlation of daily returns: {corr:.3f}")

    print("\n" + "=" * 78)
    print("INDIVIDUAL STRATEGIES (full notional each, standalone)")
    print("=" * 78)
    print(f"  Continuation alone: {fmt_daily(daily_cont, cont_stats['n_trades'])}")
    print(f"  Reversal alone:     {fmt_daily(daily_rev, rev_stats['n_trades'])}")

    print("\n" + "=" * 78)
    print("PORTFOLIO BLENDS (capital-weighted, w_cont / w_rev)")
    print("=" * 78)
    for w_cont, w_rev in [(0.5, 0.5), (0.7, 0.3), (0.3, 0.7), (1.0, 1.0)]:
        combined = w_cont * daily_cont + w_rev * daily_rev
        label = f"w=({w_cont:.1f}/{w_rev:.1f})" + ("  [full notional both]" if (w_cont, w_rev) == (1.0, 1.0) else "")
        print(f"  {label:<38} {fmt_daily(combined)}")

    print("\n" + "=" * 78)
    print("BUY & HOLD COMPARISON (same OOS window)")
    print("=" * 78)
    m5_oos = m5[m5.index >= SPLIT]
    daily_close = m5_oos["close"].resample("1D").last().dropna()
    bh_daily = daily_close.pct_change().fillna(0.0)
    bh_daily.iloc[0] -= SPREAD_BPS / 2 / 1e4
    print(f"  Buy & hold Gold: {fmt_daily(bh_daily)}")
    print(f"  Best blend above should be compared against this directly.")


if __name__ == "__main__":
    main()
