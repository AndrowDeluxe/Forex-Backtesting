"""Research script: does a higher-timeframe (4h/Daily) EMA9/21 trend-bias
filter - Baustein 3 from the FLPD paper (resources/crypto-hurst-wyckoff-
cycles.md), simplified from the failed decay-weighted Psi aggregation down
to a binary directional GATE, structurally identical to asian_range_
breakout/filters.py's already-validated SMA200 Gold trend-bias filter -
improve the auction_playbook (Fabio Valentini Auction Market Playbook
reconstruction) setups? Those have shown no edge in isolation so far (see
resources/crypto-volume-profile-mean-reversion.md's Cross-Check: BTCUSDT/
ETHUSDT 5m PF 0.83-0.84 on a 1-year sample, n=30-42).

Runs on a much longer history (2019-01-01 onward, not the original 1-year
research window) so the filter test itself has real statistical power - the
prior 1-year sample was too thin to judge ANY filter, not just this one.

Both setups (trend_continuation, mean_reversion) are tested against the
SAME HTF bias the way asian_range_breakout/filters.py's attach_trend_bias
treats direction, setup-agnostic. Structure-preserving randomization
(asian_range_breakout.randomization.dwell_preserving_test) and expanding-
window walk-forward (asian_range_breakout.walkforward.run_trend_bias_
walk_forward) are reused UNCHANGED - both are generic over any trades
DataFrame with entry_time/return_pct/aligned columns, which auction_playbook
trades already have."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.randomization import dwell_preserving_test
from asian_range_breakout.walkforward import run_trend_bias_walk_forward
from auction_playbook.data import fetch_klines
from auction_playbook.filters import attach_htf_trend_bias
from auction_playbook.metrics import trade_stats
from auction_playbook.signals import PlaybookConfig, generate_playbook_trades

START, END = "2019-01-01", "2026-08-25"
SPLIT = pd.Timestamp("2023-12-01", tz="UTC")
N_SHUFFLES = 500
HTF_VARIANTS = [("4h", "4h bias"), ("1d", "Daily bias")]


def profit_factor(trades: pd.DataFrame) -> float:
    return trade_stats(trades)["profit_factor"]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return (
        f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}  "
        f"AvgR={stats['avg_r_multiple']:+.2f}  MedR={stats['median_r_multiple']:+.2f}  "
        f"PFexBest={stats['profit_factor_excl_best_trade']:.3f}"
    )


def evaluate(sub: pd.DataFrame, label: str):
    if sub.empty:
        print(f"\n--- {label} --- (no trades)")
        return
    aligned_mask = sub["aligned"]
    aligned, misaligned = sub[aligned_mask], sub[~aligned_mask]
    is_mask = sub["entry_time"] < SPLIT

    print(f"\n--- {label} ---")
    print(f"  Unfiltered   : {fmt(trade_stats(sub))}")
    print(f"  Aligned      : {fmt(trade_stats(aligned))}")
    print(f"  Misaligned   : {fmt(trade_stats(misaligned))}")
    print(f"  IS  Aligned/Misaligned : {fmt(trade_stats(sub[aligned_mask & is_mask]))}  /  "
          f"{fmt(trade_stats(sub[~aligned_mask & is_mask]))}")
    print(f"  OOS Aligned/Misaligned : {fmt(trade_stats(sub[aligned_mask & ~is_mask]))}  /  "
          f"{fmt(trade_stats(sub[~aligned_mask & ~is_mask]))}")

    if len(sub) < 20:
        print("  (fewer than 20 trades - skipping randomization/walk-forward, not statistically meaningful)")
        return

    result = dwell_preserving_test(sub, aligned_mask, profit_factor, n_shuffles=N_SHUFFLES, seed=abs(hash(label)) % 10_000)
    print(f"  Randomization (keep aligned): actual PF={result['actual_metric']:.3f}  kept={result['n_kept']}/{result['n_total']}")
    for method in ("rotation", "run_permutation"):
        r = result[method]
        print(
            f"    [{method:>15}] null PF mean={r['null_mean']:.3f} std={r['null_std']:.3f} "
            f"[p05={r['null_p05']:.3f}, p95={r['null_p95']:.3f}]  p-value(null>=actual)={r['p_value']:.3f}"
        )

    wf = run_trend_bias_walk_forward(sub, start_test_year=2020, end_test_year=2026, min_train_trades=20)
    if wf.empty:
        print("  Walk-forward: not enough trades in any test year at min_train_trades=20.")
    else:
        print("  Walk-forward (expanding window, train-only confirmation each year):")
        print(wf.to_string(index=False))


def run_for_symbol(symbol: str):
    print(f"\n{'=' * 92}\n{symbol}\n{'=' * 92}")
    ltf = fetch_klines(symbol, "5m", START, END)
    print(f"LTF (5m): {len(ltf)} bars ({ltf.index[0].date()} -> {ltf.index[-1].date()}).")

    trades = generate_playbook_trades(ltf, PlaybookConfig())
    print(f"Raw trades generated (both setups): {len(trades)}")
    if trades.empty:
        print("No trades at all - skipping this symbol.")
        return

    for interval, htf_label in HTF_VARIANTS:
        print(f"\n{'-' * 92}\n{symbol} / {htf_label} ({interval})\n{'-' * 92}")
        htf = fetch_klines(symbol, interval, START, END)
        with_bias = attach_htf_trend_bias(trades, htf["close"], htf_bar_duration=pd.Timedelta(interval))
        print(f"Trades with a known HTF state: {len(with_bias)} / {len(trades)}")

        for setup in ["trend_continuation", "mean_reversion", None]:
            label = f"{symbol} {htf_label} - {setup or 'ALL SETUPS COMBINED'}"
            sub = (with_bias if setup is None else with_bias[with_bias["setup"] == setup]).reset_index(drop=True)
            evaluate(sub, label)


def main():
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        run_for_symbol(symbol)


if __name__ == "__main__":
    main()
