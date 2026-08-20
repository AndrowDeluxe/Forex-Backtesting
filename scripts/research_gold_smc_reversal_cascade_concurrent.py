"""Multi-position re-entry test for the reversal cascade's repeat_sweep
entry (chat 2026-08-19: "hebe die Regel nur ein Trade gleichzeitig auf.
Damit sollte es auch moeglich sein einen langen Move mehrmals zu
reentern"). Uses gold_smc_htf_ltf.concurrent_backtest.simulate_trades_
concurrent (a sibling simulator, NOT a modification of the shared
strategy.backtest.simulate_trades used by many other strategies) - every
repeat_sweep signal opens its own independent position, so a persistent
move can be re-entered multiple times while an earlier position from the
same move is still open.

First attempt at this used strategy.backtest.trades_to_daily_returns for
aggregation (compounds same-day EXITS multiplicatively, correct only when
trades are sequential) and produced a nonsense 4750% CAGR / -88% MaxDD -
with hundreds of positions overlapping, that assumption breaks completely.
Switched to gold_smc_htf_ltf.concurrent_backtest.simulate_account_reentry:
a dollar account, fixed-fractional risk_pct of CURRENT equity per trade,
multiple concurrent slots (capped by max_concurrent, tested at a few
levels including uncapped) - same engine shape as mt5_trend_pullback/
account_simulation.py, just without its "one position per market" limit.

Sweeps stop_atr x be x tp_mode(h4_level / atr) x max_hold_bars x
max_concurrent jointly. Same IS-select/OOS-validate discipline as
everything else this session.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_account_reentry, simulate_trades_concurrent,
)
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
RISK_PCT = 0.01
STARTING_EQUITY = 100_000.0

MAX_HOLD_H_CANDIDATES = [24, 48, 72, 96]
MAX_HOLD_CANDIDATES = [h * 4 for h in MAX_HOLD_H_CANDIDATES]  # M15 bars
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]
TP_VARIANTS = [("h4_level", None)] + [("atr", tp_r) for tp_r in (3.0, 5.0)]
MAX_CONCURRENT_CANDIDATES = [3, 8, None]  # None = uncapped


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def build_cfg(tp_mode: str, tp_r, stop_mult: float, be, max_hold: int) -> BacktestConfig:
    if tp_mode == "h4_level":
        return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=max_hold)
    return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=max_hold)


def summarize_concurrent(raw_trades: pd.DataFrame, index: pd.DatetimeIndex, max_concurrent: int | None) -> dict:
    sim = simulate_account_reentry(raw_trades, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=max_concurrent)
    taken = sim["trades"]
    if taken.empty:
        return {"n_trades": 0, "n_skipped": sim["n_skipped"], "win_rate": float("nan"), "profit_factor": float("nan"),
                "sharpe": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "final_equity": sim["final_equity"]}
    daily = equity_curve_to_daily_returns(sim["equity_curve"], index)
    wins = taken["pnl"] > 0
    gross_win, gross_loss = taken.loc[wins, "pnl"].sum(), -taken.loc[~wins, "pnl"].sum()
    return {
        "n_trades": len(taken), "n_skipped": sim["n_skipped"],
        "win_rate": wins.mean(), "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "sharpe": annualized_sharpe(daily), "cagr": cagr(daily), "max_drawdown": max_drawdown(daily),
        "final_equity": sim["final_equity"],
    }


def main():
    print(f"Fetching GOLD H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    sig = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
    sig_is = sig[sig.index < SPLIT]
    sig_oos = sig[sig.index >= SPLIT]
    print(f"{int((sig['signal'] != 0).sum())} raw signals (full period), {int((sig_is['signal'] != 0).sum())} in IS")

    print("\n" + "=" * 78)
    print(f"1. SWEEP (RE-ENTRY ALLOWED, $100k/1% risk account) - IS PERIOD ONLY, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    for max_hold, hours in zip(MAX_HOLD_CANDIDATES, MAX_HOLD_H_CANDIDATES):
        for tp_mode, tp_r in TP_VARIANTS:
            for stop_mult in STOP_ATR_CANDIDATES:
                for be in BE_CANDIDATES:
                    cfg = build_cfg(tp_mode, tp_r, stop_mult, be, max_hold)
                    raw_trades = simulate_trades_concurrent(sig_is, cfg)
                    for max_conc in MAX_CONCURRENT_CANDIDATES:
                        s = summarize_concurrent(raw_trades, sig_is.index, max_conc)
                        rows.append({"max_hold_h": hours, "tp_mode": tp_mode, "tp_r": tp_r, "stop_atr": stop_mult, "be": be, "max_concurrent": max_conc, **s})
        print(f"  max_hold={hours}h done")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top20 = eligible.sort_values("sharpe", ascending=False).head(20)
    print("\nTop 20 combos by IS Sharpe:")
    print(top20[["max_hold_h", "tp_mode", "tp_r", "stop_atr", "be", "max_concurrent", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]].to_string(index=False))

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['max_hold_h', 'tp_mode', 'tp_r', 'stop_atr', 'be', 'max_concurrent']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    max_hold = int(best["max_hold_h"]) * 4
    tp_mode = best["tp_mode"]
    tp_r = None if pd.isna(best["tp_r"]) else float(best["tp_r"])
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])
    max_conc = None if pd.isna(best["max_concurrent"]) else int(best["max_concurrent"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION (RE-ENTRY) - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    cfg = build_cfg(tp_mode, tp_r, stop_mult, be, max_hold)
    oos_raw = simulate_trades_concurrent(sig_oos, cfg)
    oos_stats = summarize_concurrent(oos_raw, sig_oos.index, max_conc)
    print(f"  OOS: {fmt(oos_stats)}  (final equity ${oos_stats.get('final_equity', float('nan')):,.0f}, {oos_stats.get('n_skipped', 0)} skipped at max_concurrent cap)")

    print("\n" + "=" * 78)
    print("3. BUY & HOLD + SINGLE-POSITION REFERENCE (same OOS window)")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:            Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")

    single_trades = simulate_trades(sig_oos, cfg)
    print(f"  Single-position (same cfg): {fmt(summarize(single_trades, sig_oos.index))}")
    print(f"  Re-entry (same cfg):        {fmt(oos_stats)}")
    print(f"\n  Re-entry beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    print("\n" + "=" * 78)
    print("4. max_concurrent SENSITIVITY at the winning exit config (OOS)")
    print("=" * 78)
    for mc in MAX_CONCURRENT_CANDIDATES:
        s = summarize_concurrent(oos_raw, sig_oos.index, mc)
        print(f"  max_concurrent={mc}: {fmt(s)}")


if __name__ == "__main__":
    main()
