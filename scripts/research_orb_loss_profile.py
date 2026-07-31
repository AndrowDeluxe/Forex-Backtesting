"""Since neither breakeven nor a much tighter stop (down to 0.1x M15-ATR -
stop-Anteil stays flat at 0.4-0.7% the whole way) does anything to manage
risk on this strategy, the next lever is preventing bad trades from being
entered at all, not managing them better after entry. Profiles WINNING vs.
LOSING trades (long-only + ADX>=25, full period) across entry hour, day of
week, ADX magnitude (finer buckets above the 25 floor), size of the
breakout (ATR-at-entry tercile) and holding time, on both Nasdaq and SP500,
to see whether any of these separates losers from winners cleanly enough
to be worth an entry filter.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _bucket_win_rate(trades: pd.DataFrame, by: pd.Series, label: str) -> pd.DataFrame:
    rows = []
    for key, group in trades.groupby(by, observed=True):
        wins = group["return_pct"] > 0
        gross_win = group.loc[wins, "return_pct"].sum()
        gross_loss = -group.loc[~wins, "return_pct"].sum()
        rows.append({
            label: key, "n": len(group), "win_rate": wins.mean(),
            "avg_return_bps": group["return_pct"].mean() * 1e4,
            "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        })
    return pd.DataFrame(rows).set_index(label).sort_index()


def profile(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name}: Verlust-Profil (Long-only + ADX>=25, Full-Period) {'=' * 15}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        print("  Keine Trades.")
        return

    wins = trades["return_pct"] > 0
    print(f"  Gesamt: n={len(trades)}, Gewinner={wins.sum()}, Verlierer={(~wins).sum()}, Win-Rate={wins.mean():.1%}")

    print("\n-- Einstiegsstunde (UTC) --")
    print(_bucket_win_rate(trades, trades["entry_time"].dt.hour, "hour"))

    print("\n-- Wochentag --")
    print(_bucket_win_rate(trades, trades["entry_time"].dt.day_name(), "day"))

    print("\n-- ADX-Bucket (feiner, oberhalb der 25er-Schwelle) --")
    adx_bucket = pd.cut(trades["adx_at_entry"], bins=[25, 30, 40, 50, 100], labels=["25-30", "30-40", "40-50", "50+"])
    print(_bucket_win_rate(trades, adx_bucket, "adx_bucket"))

    print("\n-- Groesse des Ausbruchs (ATR-at-Entry Tercile) --")
    try:
        atr_tercile = pd.qcut(trades["atr_at_entry"], 3, labels=["klein", "mittel", "gross"])
        print(_bucket_win_rate(trades, atr_tercile, "atr_tercile"))
    except ValueError as e:
        print(f"  (qcut fehlgeschlagen: {e})")

    print("\n-- Haltedauer (Bars, Quartile) --")
    try:
        hold_q = pd.qcut(trades["hold_bars"], 4, labels=["Q1 (kurz)", "Q2", "Q3", "Q4 (lang)"])
        print(_bucket_win_rate(trades, hold_q, "hold_quartile"))
    except ValueError as e:
        print(f"  (qcut fehlgeschlagen: {e})")

    print("\n-- Monat --")
    print(_bucket_win_rate(trades, trades["entry_time"].dt.month, "month"))


def main():
    print("Loading NASDAQ M15...")
    profile("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))

    print("\nLoading SP500 M15...")
    profile("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
