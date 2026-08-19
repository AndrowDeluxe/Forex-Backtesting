"""Final exit-parameter validation for the reversal cascade's repeat_sweep
LTF entry (chat 2026-08-19: "optimiere dafuer bitte nochmal alle
moeglichen SL, TP und BE configurationen"). v8 already thoroughly swept
tp_mode="h4_level" (mtd x stop x be, 60 combos) and found OOS
Sharpe=1.68. This ADDS the tp_mode="atr" alternative (flat R-multiple
target) that v8 never tested, matching the same two-TP-mode comparison
research_gold_smc_continuation_exit_sweep.py did for Continuation -
mtd fixed at 1.0 for the atr sweep (an entry-quality gate only there,
not the TP mechanism itself, same convention as continuation.py).
Picks the overall best (h4_level vs atr) by IS Sharpe, validates OOS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24
MAX_HOLD_BARS = H1_VALID_BARS * 4
FIXED_MTD_FOR_ATR = 1.0

STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0, 1.5]
TP_R_CANDIDATES = [1.5, 2.0, 3.0, 4.0, 5.0]

# v8's already-thorough h4_level result, carried forward as the reference to beat
H4_LEVEL_BEST = dict(mtd=1.0, stop_atr=3.0, be=None)


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    sig_atr = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=FIXED_MTD_FOR_ATR, require_ema_reject=True, m15_entry_mode="repeat_sweep")
    print(f"repeat_sweep mtd={FIXED_MTD_FOR_ATR}: {int((sig_atr['signal'] != 0).sum())} raw signals")

    print("\n" + "=" * 78)
    print(f"B) TP MODE = atr  -  IS sweep, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    sig_atr_is = sig_atr[sig_atr.index < SPLIT]
    for tp_r in TP_R_CANDIDATES:
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(sig_atr_is, cfg)
                s = summarize(trades, sig_atr_is.index)
                rows.append({"tp_mode": "atr", "tp_r": tp_r, "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} atr-mode combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if not eligible.empty:
        top10 = eligible.sort_values("sharpe", ascending=False).head(10)
        print("\nTop 10 atr-mode combos by IS Sharpe:")
        print(top10[["tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))
        atr_best = eligible.loc[eligible["sharpe"].idxmax()]
        print(f"\nBest atr-mode combo: tp_r={atr_best['tp_r']} stop={atr_best['stop_atr']} be={atr_best['be']}  {fmt(atr_best.to_dict())}")
    else:
        atr_best = None
        print("No atr-mode combo reaches the trade-count threshold.")

    # --- compare against v8's h4_level reference on the SAME IS window ---
    sig_h4level = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=H4_LEVEL_BEST["mtd"], require_ema_reject=True, m15_entry_mode="repeat_sweep")
    sig_h4level_is = sig_h4level[sig_h4level.index < SPLIT]
    cfg_h4level = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=H4_LEVEL_BEST["stop_atr"], use_vwap_target=True, breakeven_trigger_r=H4_LEVEL_BEST["be"], max_hold_bars=MAX_HOLD_BARS)
    h4level_is_trades = simulate_trades(sig_h4level_is, cfg_h4level)
    h4level_is_stats = summarize(h4level_is_trades, sig_h4level_is.index)
    print(f"\nReference (v8's h4_level best) IS: {fmt(h4level_is_stats)}")

    use_atr = atr_best is not None and atr_best["sharpe"] > h4level_is_stats["sharpe"]
    print(f"\n{'ATR mode wins on IS Sharpe' if use_atr else 'h4_level mode remains the winner on IS Sharpe'} - validating that one on OOS.")

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    if use_atr:
        sig_oos = sig_atr[sig_atr.index >= SPLIT]
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=float(atr_best["stop_atr"]), use_vwap_target=False, take_profit_r=float(atr_best["tp_r"]), breakeven_trigger_r=(None if pd.isna(atr_best["be"]) else float(atr_best["be"])), max_hold_bars=MAX_HOLD_BARS)
        label = f"atr tp_r={atr_best['tp_r']} stop={atr_best['stop_atr']} be={atr_best['be']}"
    else:
        sig_oos = sig_h4level[sig_h4level.index >= SPLIT]
        cfg = cfg_h4level
        label = f"h4_level stop={H4_LEVEL_BEST['stop_atr']} be={H4_LEVEL_BEST['be']}"
    print(f"  Config: {label}")
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("OUTLIER-SENSITIVITY CHECK ON OOS")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, sig_oos.index)
        print(f"  OOS PF with best trade:    {oos_stats['profit_factor']:.3f}  (Sharpe {oos_stats['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")

    print("\n" + "=" * 78)
    print("BUY & HOLD COMPARISON")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   {fmt(oos_stats)}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")


if __name__ == "__main__":
    main()
