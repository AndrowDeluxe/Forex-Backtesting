"""Research script: an ORIGINAL long-only Gold (XAUUSD) trend-pullback
strategy with a fixed ATR stop and fixed R-multiple take-profit.

Built as an independent reference point for the publicly stated concept
behind the paid "Smart Gold Hunter" MQL5-Market EA (long-only, real Stop
Loss/Take Profit, no grid, no martingale, controlled risk management) - see
chat for context. That EA is closed-source (compiled .ex5 only, no .mq5)
and was never inspected; nothing here is derived from its code - own signal
(EMA trend + pullback trigger), own package (gold_trend_pullback_atr/), real
Dukascopy Gold M15 bars (same feed asian_range_breakout already uses).

Rigor pattern matches scripts/research_gold_pullback_ma_strategy.py: sweep
-> IS/OOS breakdown at the standout combo -> regime decomposition.

Cost assumption: spread_bps=10.0 round-trip, the "Realistic" gold tier
already used in scripts/research_gold_bitcoin_dual_momentum_costs.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from gold_trend_pullback_atr.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import regime_decomposition, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="America/New_York")
SPREAD_BPS = 10.0

TREND_EMA_CANDIDATES = [100, 200]
FAST_EMA_CANDIDATES = [10, 20, 50]
STOP_ATR_CANDIDATES = [1.5, 2.0, 3.0]
TP_R_CANDIDATES = [1.5, 2.0, 3.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    print(f"{len(df)} M15 bars")

    print("\n" + "=" * 78)
    print(f"1. PARAMETER SWEEP (full period, spread_bps={SPREAD_BPS})")
    print("=" * 78)
    rows = []
    for trend_ema in TREND_EMA_CANDIDATES:
        for fast_ema in FAST_EMA_CANDIDATES:
            signaled = run_pipeline(df, trend_ema=trend_ema, fast_ema=fast_ema)
            for stop_mult in STOP_ATR_CANDIDATES:
                for tp_r in TP_R_CANDIDATES:
                    cfg = BacktestConfig(
                        spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult,
                        use_vwap_target=False, take_profit_r=tp_r,
                    )
                    trades = simulate_trades(signaled, cfg)
                    s = summarize(trades, signaled.index)
                    rows.append({"trend_ema": trend_ema, "fast_ema": fast_ema, "stop_atr": stop_mult, "tp_r": tp_r, **s})
                    print(f"  trend={trend_ema:>3} fast={fast_ema:>2} stop={stop_mult} tp={tp_r}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= 30]
    if eligible.empty:
        print("\nNo combo reaches 30 trades - stopping, material too thin to draw conclusions.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest Sharpe, n>=30):\n{best[['trend_ema', 'fast_ema', 'stop_atr', 'tp_r']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    te, fe = int(best["trend_ema"]), int(best["fast_ema"])
    sm, tr = float(best["stop_atr"]), float(best["tp_r"])
    signaled = run_pipeline(df, trend_ema=te, fast_ema=fe)
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=sm, use_vwap_target=False, take_profit_r=tr)
    trades = simulate_trades(signaled, cfg)

    print("\n" + "=" * 78)
    print(f"2. IS/OOS BREAKDOWN (split={SPLIT.date()})")
    print("=" * 78)
    is_trades = trades[trades["entry_time"] < SPLIT]
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    print(f"  Full: {fmt(summarize(trades, signaled.index))}")
    print(f"  IS  : {fmt(summarize(is_trades, signaled[signaled.index < SPLIT].index))}")
    print(f"  OOS : {fmt(summarize(oos_trades, signaled[signaled.index >= SPLIT].index))}")

    print("\n" + "=" * 78)
    print("3. REGIME DECOMPOSITION (trend strength x volatility tercile at entry)")
    print("=" * 78)
    print(regime_decomposition(trades).to_string(index=False))

    print("\n" + "=" * 78)
    print("4. EXIT REASON BREAKDOWN")
    print("=" * 78)
    print(trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
