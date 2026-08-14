"""Research script: backtest of the community "MT5 Trend+Pullback Bot"
(see `.../Bots/Ideen1/MT5-TrendPullback-Bot/` - a live Python/MetaTrader5
bot the user already runs on a demo account) on this repo's real Dukascopy
data, using the bot's own indicator formulas and parameters unchanged
(mt5_trend_pullback/pipeline.py) so results here should line up with what
the live bot has been doing/would do on the same bars.

Markets and timeframes match config.py's `MARKETS` dict exactly: Gold,
Silver, Platinum on H1; CHFJPY, USDJPY on H4. Strategy parameters
(EMA150 trend filter, RSI14 oversold=35, ATR14 stop x2.0, RR 2.0, long-only)
match config.py's "neutral, robustness-tested" values, not any per-market
overfit variant.

Cost assumption: round-trip spread_bps per market is a labelled *assumption*
(this repo has no historical bid/ask spread feed), not measured - metals
follow the 10.0bps "Realistic" gold tier already used in
scripts/research_gold_trend_pullback_atr.py; USDJPY (deep FX major) and
CHFJPY (thinner cross) get lighter, distinct FX-typical assumptions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import (
    ATR_STOP_MULT, RR_RATIO, RSI_LEN, RSI_OVERSOLD, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import regime_decomposition, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")

# (data key, timeframe, MT5 symbol label, round-trip spread assumption in bps)
MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
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


def main():
    print("=" * 78)
    print(f"MT5 TREND+PULLBACK BOT REPLICATION  "
          f"(EMA{TREND_LEN} trend, RSI{RSI_LEN} oversold={RSI_OVERSOLD}, "
          f"ATR x{ATR_STOP_MULT}, RR {RR_RATIO}, long-only)")
    print("=" * 78)

    all_trades = {}
    for key, tf, label, spread_bps in MARKETS:
        print(f"\nFetching {label} {tf} {START} -> {END} ...")
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        print(f"  {len(df)} {tf} bars")

        signaled = run_pipeline(df)
        cfg = BacktestConfig(
            spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT,
            use_vwap_target=False, take_profit_r=RR_RATIO,
        )
        trades = simulate_trades(signaled, cfg)
        trades["market"] = label
        all_trades[label] = (trades, signaled)

        s = summarize(trades, signaled.index)
        print(f"  Full : {fmt(s)}")
        is_trades = trades[trades["entry_time"] < SPLIT]
        oos_trades = trades[trades["entry_time"] >= SPLIT]
        print(f"  IS   : {fmt(summarize(is_trades, signaled[signaled.index < SPLIT].index))}")
        print(f"  OOS  : {fmt(summarize(oos_trades, signaled[signaled.index >= SPLIT].index))}")

    print("\n" + "=" * 78)
    print("PORTFOLIO (all 5 markets combined, no MAX_OPEN_POSITIONS cap applied)")
    print("=" * 78)
    combined = pd.concat([t for t, _ in all_trades.values()], ignore_index=True).sort_values("entry_time")
    full_index = pd.date_range(
        min(sig.index.min() for _, sig in all_trades.values()),
        max(sig.index.max() for _, sig in all_trades.values()),
        freq="D",
    )
    print(f"  Full : {fmt(summarize(combined, full_index))}")
    print(f"  Trades/week (avg, all markets): {len(combined) / ((full_index[-1] - full_index[0]).days / 7):.2f}")

    print("\n" + "=" * 78)
    print("EXIT REASON BREAKDOWN (combined)")
    print("=" * 78)
    print(combined["exit_reason"].value_counts().to_string())

    print("\n" + "=" * 78)
    print("REGIME DECOMPOSITION (combined, trend strength x volatility tercile)")
    print("=" * 78)
    print(regime_decomposition(combined).to_string(index=False))


if __name__ == "__main__":
    main()
