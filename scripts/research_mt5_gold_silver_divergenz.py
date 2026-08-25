"""Research script: backtest of the community "Divergenz Gold/Silber" MT5 bot
(see `.../Bots/Neue Bots/3-Divergenz-Gold-Silber/` -- long-only Gold,
Silver used only as a reference/never traded) on this repo's real Dukascopy
data, using the bot's own indicator/signal formulas unchanged
(mt5_gold_silver_divergenz/pipeline.py) so results here line up with what the
live bot would do on the same bars. Signal parity verified bit-exact against
the live bot's own check_signal() bar-by-bar (2016-2020 H4, 0 mismatches out
of 6393 bars) before trusting anything below.

Market/timeframe matches config.py exactly: XAUUSD H4 (traded), XAGUSD H4
(reference only). Strategy parameters (EMA150 trend filter, 20-bar momentum
difference vs. its own 100-bar -1.5-sigma band, ATR14 stop x2.0, RR 2.0,
long-only) match config.py's shipped values.

config.py claims a prior research result (OOS ratio 2.43-2.65, 142 trades/
10yr, top-5-trade concentration 10.7%) from a script this machine has no
record of (see mt5_gold_silver_divergenz/pipeline.py's module docstring) --
this script is an independent reconstruction, not a re-run of that exact
prior methodology, so don't expect the numbers below to reproduce those
exactly.

Cost assumption: 10.0bps round-trip, the "Realistic" gold tier already used
in scripts/research_gold_trend_pullback_atr.py and
scripts/research_mt5_trend_pullback.py (this repo has no historical bid/ask
spread feed).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_gold_silver_divergenz.pipeline import (
    ATR_STOP_MULT, BAND_LOOKBACK, BAND_MULT, RET_LEN, RR_RATIO, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import regime_decomposition, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
SPREAD_BPS = 10.0


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print("=" * 78)
    print(f"MT5 GOLD/SILBER-DIVERGENZ BOT REPLICATION  "
          f"(EMA{TREND_LEN} trend, {RET_LEN}-bar Momentum-Diff vs. "
          f"{BAND_LOOKBACK}-bar {BAND_MULT}-sigma band, ATR x{ATR_STOP_MULT}, "
          f"RR {RR_RATIO}, XAUUSD long-only, XAGUSD reference)")
    print("=" * 78)

    print(f"\nFetching XAUUSD H4 {START} -> {END} ...")
    xau = fetch_timeframe("GOLD", "H4", START, END)
    xau = xau.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    print(f"  {len(xau)} H4 bars")

    print(f"Fetching XAGUSD H4 {START} -> {END} ...")
    xag = fetch_timeframe("SILVER", "H4", START, END)
    xag = xag.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    print(f"  {len(xag)} H4 bars")

    signaled = run_pipeline(xau, xag)
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(signaled, cfg)

    s = summarize(trades, signaled.index)
    print(f"\n  Full : {fmt(s)}")
    is_trades = trades[trades["entry_time"] < SPLIT]
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    print(f"  IS   : {fmt(summarize(is_trades, signaled[signaled.index < SPLIT].index))}")
    print(f"  OOS  : {fmt(summarize(oos_trades, signaled[signaled.index >= SPLIT].index))}")

    print("\n" + "=" * 78)
    print("EXIT REASON BREAKDOWN")
    print("=" * 78)
    print(trades["exit_reason"].value_counts().to_string())

    print("\n" + "=" * 78)
    print("PROFIT CONCENTRATION (Top-N-Trades share of gross profit)")
    print("=" * 78)
    wins = trades[trades["return_pct"] > 0].sort_values("return_pct", ascending=False)
    gross_profit = wins["return_pct"].sum()
    for n in (1, 3, 5, 10):
        top_n = wins["return_pct"].head(n).sum()
        print(f"  Top-{n:<2}: {top_n / gross_profit:.1%} des Bruttogewinns" if gross_profit > 0 else "  n/a")

    print("\n" + "=" * 78)
    print("REGIME DECOMPOSITION (trend strength x volatility tercile)")
    print("=" * 78)
    print(regime_decomposition(trades).to_string(index=False))


if __name__ == "__main__":
    main()
