"""Professional-backtest step 2/N (chat 2026-08-20): walk-forward / extended-
history validation. Everything so far (entry logic, exits, trend filter,
risk sizing) was IS-selected on 2024-08-01/2025-08-01 and OOS-validated on
2025-08-01/2026-08-01 - both strategies have NEVER seen 2016-2024. Running
the FINAL, LOCKED configs (no re-tuning) against that much longer, wholly
untouched period is a genuine additional out-of-sample test: does the edge
generalise across regimes (2016-2020 range-bound gold, 2020 COVID crash,
2022 rate-hike bear phase, 2023-24 breakout), or was it curve-fit to the
recent 2-year bull run specifically? Reported both as one aggregate block
and split into ~2-year sub-periods so a regime-specific failure doesn't
hide inside a flattering full-period average.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

WF_START, WF_END = "2016-01-01", "2024-08-01"
SPREAD_BPS = 8.0

SUB_PERIODS = [
    ("2016-01-01", "2018-08-01"),
    ("2018-08-01", "2020-08-01"),
    ("2020-08-01", "2022-08-01"),
    ("2022-08-01", "2024-08-01"),
]

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {WF_START} -> {WF_END} (walk-forward, wholly unseen period) ...")
    h4 = fetch_gold_h4(WF_START, WF_END)
    h1 = fetch_gold_h1(WF_START, WF_END)
    m15 = fetch_gold_m15(WF_START, WF_END)
    m5 = fetch_gold_m5(WF_START, WF_END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    print("\nGenerating signals over the FULL walk-forward window (final, locked configs, no re-tuning) ...")
    cont_sig_full = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    rev_sig_full = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)

    print("\n" + "=" * 100)
    print(f"CONTINUATION - full walk-forward window {WF_START} -> {WF_END}")
    print("=" * 100)
    cont_trades_full = simulate_trades(cont_sig_full, CONT_BACKTEST_CFG)
    print(f"  {fmt(summarize(cont_trades_full, cont_sig_full.index))}")

    print("\n" + "=" * 100)
    print(f"REVERSAL-KASKADE - full walk-forward window {WF_START} -> {WF_END} (single-position reference)")
    print("=" * 100)
    rev_trades_full = simulate_trades(rev_sig_full, REV_BACKTEST_CFG)
    print(f"  {fmt(summarize(rev_trades_full, rev_sig_full.index))}")

    m15_full = m15
    daily_close = m15_full["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    print(f"\n  Buy & Hold (voller WF-Zeitraum): Sharpe={annualized_sharpe(daily_ret):.2f}  CAGR={cagr(daily_ret):+.1%}  MaxDD={max_drawdown(daily_ret):.1%}")

    print("\n" + "=" * 100)
    print("SUB-PERIODEN (~2 Jahre je Regime-Fenster)")
    print("=" * 100)
    for sp_start, sp_end in SUB_PERIODS:
        sp_start_ts, sp_end_ts = pd.Timestamp(sp_start, tz="America/New_York"), pd.Timestamp(sp_end, tz="America/New_York")
        cont_sig_sp = cont_sig_full[(cont_sig_full.index >= sp_start_ts) & (cont_sig_full.index < sp_end_ts)]
        rev_sig_sp = rev_sig_full[(rev_sig_full.index >= sp_start_ts) & (rev_sig_full.index < sp_end_ts)]
        cont_trades_sp = simulate_trades(cont_sig_sp, CONT_BACKTEST_CFG)
        rev_trades_sp = simulate_trades(rev_sig_sp, REV_BACKTEST_CFG)
        daily_close_sp = m15_full.loc[sp_start_ts:sp_end_ts, "close"].resample("1D").last().dropna()
        daily_ret_sp = daily_close_sp.pct_change().fillna(0.0)
        bh_sharpe_sp = annualized_sharpe(daily_ret_sp) if len(daily_ret_sp) > 5 else float("nan")
        print(f"\n  {sp_start} -> {sp_end}")
        print(f"    Continuation:      {fmt(summarize(cont_trades_sp, cont_sig_sp.index))}")
        print(f"    Reversal-Kaskade:  {fmt(summarize(rev_trades_sp, rev_sig_sp.index))}")
        print(f"    Buy & Hold Sharpe: {bh_sharpe_sp:.2f}")


if __name__ == "__main__":
    main()
