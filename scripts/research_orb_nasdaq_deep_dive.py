"""Deep dive on the ORB strategy's standout first-pass result (Nasdaq, M15,
+0.59 pooled / +0.55 mean-yearly Sharpe, see chat) with the stop fixed to
size off M15-scale ATR instead of the daily ATR used for the threshold
itself (the earlier run's stop almost never triggered - >99% of trades
just rode to session_end regardless of intraday drawdown).

Breaks results down by: calendar year, day-level volatility regime
("expansion" vs "contraction", per orb_strategy.pipeline.compute_orb_frame),
bar-level ADX x ATR-tercile regime (strategy.metrics.regime_decomposition,
the same tool used for the ADX-VWAP paper's Sec. 7), long vs. short, day of
week, and entry hour - to see where, specifically, this result lives rather
than trusting one pooled number.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import attach_vol_regime, run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import regime_decomposition, summarize, trade_stats

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2027))
START, END = "2016-07-28", "2026-07-28"


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _bucket_table(trades: pd.DataFrame, by: pd.Series, label: str) -> pd.DataFrame:
    rows = []
    for key, group in trades.groupby(by):
        s = trade_stats(group)
        s.pop("exit_reason_counts", None)
        s["avg_return_bps"] = s.pop("avg_return_pct") * 1e4
        rows.append({label: key, **s})
    return pd.DataFrame(rows).set_index(label)


def main():
    print("Loading NASDAQ M15 (cached after first run)...")
    df = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0)

    print("\n" + "=" * 20 + " Stop calibration (M15-ATR based) " + "=" * 20)
    for mult in [1.0, 2.0, 3.0, 4.0]:
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=mult, use_vwap_target=False)
        trades = simulate_trades(signaled, cfg)
        print(f"stop_atr_mult={mult}: n={len(trades)}, exit_reasons={trades['exit_reason'].value_counts().to_dict()}")

    STOP_MULT = 2.0
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    trades = attach_vol_regime(trades, signaled)
    print(f"\nUsing stop_atr_mult={STOP_MULT} for everything below. Total trades: {len(trades)}")

    full = summarize(trades, signaled.index)
    print("\nFull-period:", {k: v for k, v in full.items() if k != "exit_reason_counts"})
    print("Exit reasons:", trades["exit_reason"].value_counts().to_dict())

    print("\n" + "=" * 20 + " Yearly walk-forward " + "=" * 20)
    rows = []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        yr_trades = trades[trades["entry_time"].dt.year == year]
        if yr_trades.empty:
            rows.append({"year": year, "n_trades": 0})
            continue
        s = summarize(yr_trades, yr_df.index)
        rows.append(
            {
                "year": year, "n_trades": s["n_trades"], "win_rate": s["win_rate"],
                "avg_return_bps": s["avg_return_pct"] * 1e4, "sharpe": s["sharpe"],
                "profit_factor": s["profit_factor"],
            }
        )
    yearly = pd.DataFrame(rows).set_index("year")
    print(yearly)
    active = yearly[yearly["n_trades"] > 0]
    print(f"Mean Sharpe across active years: {active['sharpe'].mean():.2f}")
    print(f"Years with positive avg return: {(active['avg_return_bps'] > 0).sum()}/{len(active)}")

    print("\n" + "=" * 20 + " Tages-Volatilitaetsregime (Contraction/Expansion) " + "=" * 20)
    print(_bucket_table(trades.dropna(subset=["vol_regime"]), trades.dropna(subset=["vol_regime"])["vol_regime"], "vol_regime"))

    print("\n" + "=" * 20 + " Bar-Regime (ADX-Bucket x ATR-Tercile, strategy.metrics.regime_decomposition) " + "=" * 20)
    print(regime_decomposition(trades))

    print("\n" + "=" * 20 + " Long vs. Short " + "=" * 20)
    direction_label = trades["direction"].map({1: "Long", -1: "Short"})
    print(_bucket_table(trades, direction_label, "direction"))

    print("\n" + "=" * 20 + " Wochentag " + "=" * 20)
    dow = trades["entry_time"].dt.day_name()
    print(_bucket_table(trades, dow, "day_of_week"))

    print("\n" + "=" * 20 + " Einstiegsstunde (UTC) " + "=" * 20)
    hour = trades["entry_time"].dt.hour
    print(_bucket_table(trades, hour, "entry_hour"))

    print("\n" + "=" * 20 + " Kombiniert: Vol-Regime x Richtung " + "=" * 20)
    combo = trades.dropna(subset=["vol_regime"]).copy()
    combo["direction_label"] = combo["direction"].map({1: "Long", -1: "Short"})
    rows = []
    for keys, group in combo.groupby(["vol_regime", "direction_label"]):
        s = trade_stats(group)
        s.pop("exit_reason_counts", None)
        s["avg_return_bps"] = s.pop("avg_return_pct") * 1e4
        rows.append({"vol_regime": keys[0], "direction": keys[1], **s})
    print(pd.DataFrame(rows).set_index(["vol_regime", "direction"]))


if __name__ == "__main__":
    main()
