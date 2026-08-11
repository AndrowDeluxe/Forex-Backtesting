"""Research script: US 10-year Treasury yield (DGS10) as a third cross-asset
context filter for the Gold Asian-Range Breakout, alongside the DXY-alignment
and VIX-change-rate filters already tested in
research_gold_dxy_vix_change_filters.py (2026-08-06). Judged against the same
ADX-filtered production config - the one strategy in this repo with an
actual edge - not the raw baseline.

Hypothesis (real-rate channel, standard Gold literature - e.g. Erb & Harvey):
Gold pays no yield, so its opportunity cost rises with the rate on the
risk-free alternative. Long trades taken while the US 10y yield has been
FALLING, and short trades taken while it has been RISING, should hold up
better than trades fighting that backdrop - structurally the same
"aligned/misaligned" framing as the existing DXY filter, just yields instead
of the dollar index, and a genuinely daily, directly-observed series (DGS10
via FRED) rather than a proxy.

Provenance: DGS10 loader is bond_yield_indicator.fred.fetch_yield("US"),
reused as-is from the Bond-Yield-Spread-Indikator build (see knowledge/
projects/bond-yield-spread-indikator.md) rather than duplicated here - it is
the one series from that project that turned out to be genuinely daily and
therefore worth reusing on its own, independent of that project's own
(inconclusive) FX result.

Same discipline as every other filter test in this repo: full period, IS/OOS
split (2021-01-01), and a window-length sensitivity sweep before trusting any
single number - a filter that only "works" at one arbitrary window is noise,
not a finding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter, attach_series_change
from bond_yield_indicator.fred import fetch_yield
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
WINDOWS = [3, 5, 10, 20]


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    gold = fetch_gold_m15(START, END)
    trades_all = simulate_asian_breakout(gold)
    trades = apply_adx_filter(trades_all, adx_min=15)
    print(f"{len(trades_all)} raw trades, {len(trades)} after the production ADX<15 filter.")

    print("\nFetching US 10y yield (DGS10, FRED) ...")
    dgs10 = fetch_yield("US")
    dgs10 = dgs10[(dgs10.index >= "2015-06-01") & (dgs10.index <= END)]
    print(f"{len(dgs10)} daily observations, {dgs10.index.min().date()} .. {dgs10.index.max().date()}")

    is_long = trades["direction"] == "long"

    # =========================================================================
    # 1. Yield-alignment: window sensitivity sweep (full period only)
    # =========================================================================
    print("\n" + "=" * 78)
    print("1. US-10Y-YIELD-ALIGNMENT -- window sensitivity sweep (full period)")
    print("=" * 78)
    print("Aligned  = long while yield falling, short while yield rising (real-rate tailwind)")
    print("Misaligned = long while yield rising, short while yield falling (fighting real rates)")
    print(f"{'window':>6}  {'aligned':<28}  {'misaligned':<28}  {'neutral(chg==0)':<15}")
    for w in WINDOWS:
        t = attach_series_change(trades, dgs10, "yield_chg", window=w)
        t = t.dropna(subset=["yield_chg"])
        yield_up = t["yield_chg"] > 0
        yield_down = t["yield_chg"] < 0
        aligned_mask = (is_long[t.index] & yield_down) | (~is_long[t.index] & yield_up)
        misaligned_mask = (is_long[t.index] & yield_up) | (~is_long[t.index] & yield_down)
        aligned = trade_stats(t[aligned_mask])
        misaligned = trade_stats(t[misaligned_mask])
        neutral_n = int((t["yield_chg"] == 0).sum())
        print(f"{w:>6}  {fmt(aligned):<28}  {fmt(misaligned):<28}  {neutral_n:<15}")

    # =========================================================================
    # 2. Yield-alignment: full IS/OOS breakdown at window=5
    # =========================================================================
    W = 5
    print("\n" + "=" * 78)
    print(f"2. US-10Y-YIELD-ALIGNMENT -- IS/OOS breakdown at window={W}")
    print("=" * 78)
    t5 = attach_series_change(trades, dgs10, "yield_chg", window=W).dropna(subset=["yield_chg"])
    is_long5 = t5["direction"] == "long"
    yield_up = t5["yield_chg"] > 0
    yield_down = t5["yield_chg"] < 0
    aligned_mask = (is_long5 & yield_down) | (~is_long5 & yield_up)
    misaligned_mask = (is_long5 & yield_up) | (~is_long5 & yield_down)

    is_period = t5["entry_time"] < SPLIT
    oos_period = t5["entry_time"] >= SPLIT

    print(f"{'':<12}{'Aligned':<28}{'Misaligned':<28}")
    print(f"{'Full':<12}{fmt(trade_stats(t5[aligned_mask])):<28}{fmt(trade_stats(t5[misaligned_mask])):<28}")
    print(
        f"{'IS':<12}{fmt(trade_stats(t5[aligned_mask & is_period])):<28}"
        f"{fmt(trade_stats(t5[misaligned_mask & is_period])):<28}"
    )
    print(
        f"{'OOS':<12}{fmt(trade_stats(t5[aligned_mask & oos_period])):<28}"
        f"{fmt(trade_stats(t5[misaligned_mask & oos_period])):<28}"
    )


if __name__ == "__main__":
    main()
