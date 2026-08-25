"""Research script: backtest of the community "David-V2" MT5 bot (see
`.../Bots/Neue Bots/2-David-V2/` -- a long+short evolution of the Haupt-Bot
Trend+Pullback idea, not yet deployed live anywhere on this machine, unlike
Haupt-Bot's `TrendPullback-Bot/`) on this repo's real Dukascopy data, using
the bot's own indicator formulas and parameters unchanged
(mt5_david_v2/pipeline.py) so results here line up with what the live bot
would do on the same bars.

Markets and timeframes match config.py's `MARKETS` dict exactly: EURUSD,
GBPUSD, USDJPY on H1; Gold on H4. Strategy parameters (EMA200 trend filter
+/- 0.25 ATR neutral zone, RSI14 mirrored 35/65, ATR14 stop x1.5, RR 2.0,
long AND short) match config.py's shipped defaults.

NOT modelled here (disclosed simplification, documented in
knowledge/projects/mt5-david-v2-pullback.md): SECURE_PROFIT stop-trailing
(equity-percent-based, triggers at +0.8% locks +0.1%) and the daily
loss/profit halt (-1.0%/+5.0% of equity) are live-only overlays that don't
fit strategy.backtest.simulate_trades' per-market, R-multiple-based engine --
this backtest validates the entry/exit EDGE (fixed SL/TP at entry, matching
what the bot actually sends to the broker), not the full live risk-management
wrapper around it.

Cost assumption: round-trip spread_bps per market is a labelled *assumption*
(this repo has no historical bid/ask spread feed) -- FX majors get a tight
FX-typical assumption, Gold reuses the 10.0bps "Realistic" gold tier already
used in scripts/research_gold_trend_pullback_atr.py and
scripts/research_mt5_trend_pullback.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_david_v2.pipeline import (
    ATR_STOP_MULT, RR_RATIO, RSI_LEN, RSI_OVERSOLD, TREND_BUFFER_ATR, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import regime_decomposition, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")

# (data key, timeframe, MT5 symbol label, round-trip spread assumption in bps)
MARKETS = [
    ("EURUSD", "H1", "EURUSD", 1.5),
    ("GBPUSD", "H1", "GBPUSD", 2.0),
    ("USDJPY", "H1", "USDJPY", 1.5),
    ("GOLD", "H4", "XAUUSD", 10.0),
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
    print(f"MT5 DAVID-V2 BOT REPLICATION  "
          f"(EMA{TREND_LEN}+/-{TREND_BUFFER_ATR}ATR trend, RSI{RSI_LEN} "
          f"{RSI_OVERSOLD:.0f}/{100 - RSI_OVERSOLD:.0f}, ATR x{ATR_STOP_MULT}, "
          f"RR {RR_RATIO}, long+short)")
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

        longs, shorts = trades[trades["direction"] == 1], trades[trades["direction"] == -1]
        print(f"  Long : {fmt(summarize(longs, signaled.index))}   "
              f"Short: {fmt(summarize(shorts, signaled.index))}")

    print("\n" + "=" * 78)
    print("PORTFOLIO (all 4 markets combined, no MAX_OPEN_POSITIONS cap applied)")
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
