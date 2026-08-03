"""Illustrative sanity-check, NOT a statistical validation: runs the
confirmed ORB long-only + ADX>=25 + weekday-filter pipeline against REAL
broker price data (TTP demo, Konto 2) instead of Dukascopy, for whatever
short window the broker actually has available (~March 2026 onward - see
chat, larger history requests returned 0 bars). The point is only to check
that the signal logic fires sensibly on a genuine broker feed and that
trade characteristics (direction split, rough win rate) are in the same
ballpark as the Dukascopy-based research - 4-5 months is nowhere near
enough for a Sharpe/PF number anyone should trust.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import MetaTrader5 as mt5

from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

TERMINAL_PATH = r"C:\Users\andre\MT5-Terminals\TTP MT5 Terminal - Konto2\terminal64.exe"
ASSET_CONFIG = {"USTEC": "Thursday", "US500": "Monday"}  # mirrors NASDAQ/SP500 weekday filters


def fetch_mt5_m15(symbol: str, n_bars: int = 10_000) -> pd.DataFrame:
    if not mt5.initialize(path=TERMINAL_PATH):
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, n_bars)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"no bars returned for {symbol}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time").rename(columns={"tick_volume": "volume"})
    return df[["open", "high", "low", "close", "volume"]]


def run_asset(symbol: str, exclude_weekday: str):
    print(f"\n{'=' * 15} {symbol} (TTP-Broker-Daten, Konto 2) {'=' * 15}")
    df = fetch_mt5_m15(symbol)
    print(f"Zeitraum: {df.index.min()} bis {df.index.max()} ({len(df)} Bars)")

    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=exclude_weekday)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)

    print(f"Trades: {len(trades)}")
    if trades.empty:
        print("  Keine Trades in diesem kurzen Fenster.")
        return
    s = summarize(trades, signaled.index)
    print(f"  sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}, avg_bps={s['avg_return_pct']*1e4:.2f}")
    print(f"  Exit-Gruende: {trades['exit_reason'].value_counts().to_dict()}")
    print("\n  Einzelne Trades:")
    print(trades[["entry_time", "direction", "entry_price", "exit_price", "return_pct", "exit_reason"]].to_string(index=False))


def main():
    for symbol, weekday in ASSET_CONFIG.items():
        run_asset(symbol, weekday)


if __name__ == "__main__":
    main()
