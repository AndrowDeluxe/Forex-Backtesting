"""In-sample exploration + a single, un-peeked out-of-sample check.

Methodology (Sec. 7's own warning about data-snooping, Sullivan/Timmermann/
White): candidates are ranked using ONLY the in-sample window
(2016-07-28 .. 2023-07-28). Whichever candidate wins in-sample is then
evaluated on the out-of-sample window (2023-07-28 .. 2026-07-28) exactly
once, and that number is reported as-is — no re-tuning after seeing it.
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.data import PAIRS
from strategy.metrics import summarize
from strategy.real_data import load_all_pairs_real
from strategy.signals import run_indicator_pipeline

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

SPLIT_DATE = pd.Timestamp("2023-07-28", tz="UTC")
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)

CANDIDATES = {
    "baseline": dict(adx_ceiling=None, theta_multiplier=1.0, stop_atr_mult=0.5),
    "adx_ceiling_25": dict(adx_ceiling=25.0, theta_multiplier=1.0, stop_atr_mult=0.5),
    "adx_ceiling_20": dict(adx_ceiling=20.0, theta_multiplier=1.0, stop_atr_mult=0.5),
    "adx_ceiling_25_tighter_stop": dict(adx_ceiling=25.0, theta_multiplier=1.0, stop_atr_mult=0.25),
    "adx_ceiling_25_wider_theta": dict(adx_ceiling=25.0, theta_multiplier=1.5, stop_atr_mult=0.5),
    "theta_1.5x": dict(adx_ceiling=None, theta_multiplier=1.5, stop_atr_mult=0.5),
    "stop_1.0x": dict(adx_ceiling=None, theta_multiplier=1.0, stop_atr_mult=1.0),
}


def backtest_slice(signaled: pd.DataFrame, stop_atr_mult: float, start=None, end=None) -> dict:
    sliced = signaled
    if start is not None:
        sliced = sliced[sliced.index >= start]
    if end is not None:
        sliced = sliced[sliced.index < end]
    cfg = replace(BASE_CONFIG, stop_atr_mult=stop_atr_mult)
    trades = simulate_trades(sliced, cfg)
    return summarize(trades, sliced.index)


def main():
    print("Loading real Dukascopy history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28")

    print(f"\n=== In-sample screen (2016-07-28 .. {SPLIT_DATE.date()}) ===")
    rows = []
    for name, params in CANDIDATES.items():
        pair_sharpes, pair_returns, pair_trades = [], [], []
        for pair in PAIRS:
            signaled = run_indicator_pipeline(
                data[pair],
                adx_ceiling=params["adx_ceiling"],
                theta_multiplier=params["theta_multiplier"],
            )
            s = backtest_slice(signaled, params["stop_atr_mult"], end=SPLIT_DATE)
            pair_sharpes.append(s["sharpe"])
            pair_returns.append(s["avg_return_pct"])
            pair_trades.append(s["n_trades"])
        rows.append(
            {
                "candidate": name,
                "mean_sharpe": sum(pair_sharpes) / len(pair_sharpes),
                "pairs_sharpe_pos": sum(sh > 0 for sh in pair_sharpes),
                "mean_avg_return_bps": sum(pair_returns) / len(pair_returns) * 1e4,
                "min_trades": min(pair_trades),
                "total_trades": sum(pair_trades),
            }
        )
        print(f"  {name:30s} done")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)

    winner_name = screen.index[0]
    winner = CANDIDATES[winner_name]
    print(f"\n=== Winner (in-sample): {winner_name} -> {winner} ===")

    print(f"\n=== Out-of-sample check ({SPLIT_DATE.date()} .. 2026-07-28), evaluated once ===")
    oos_rows = []
    for pair in PAIRS:
        signaled = run_indicator_pipeline(
            data[pair], adx_ceiling=winner["adx_ceiling"], theta_multiplier=winner["theta_multiplier"]
        )
        s = backtest_slice(signaled, winner["stop_atr_mult"], start=SPLIT_DATE)
        oos_rows.append({"pair": pair, **s})
    oos = pd.DataFrame(oos_rows).set_index("pair")
    print(oos[["n_trades", "win_rate", "avg_return_pct", "sharpe", "calmar", "max_drawdown"]])

    print(f"\n=== Baseline for comparison, same out-of-sample window ===")
    base_rows = []
    for pair in PAIRS:
        signaled = run_indicator_pipeline(data[pair])
        s = backtest_slice(signaled, BASE_CONFIG.stop_atr_mult, start=SPLIT_DATE)
        base_rows.append({"pair": pair, **s})
    base = pd.DataFrame(base_rows).set_index("pair")
    print(base[["n_trades", "win_rate", "avg_return_pct", "sharpe", "calmar", "max_drawdown"]])


if __name__ == "__main__":
    main()
