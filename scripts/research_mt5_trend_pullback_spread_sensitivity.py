"""Follow-up to scripts/research_mt5_trend_pullback.py and
scripts/research_mt5_trend_pullback_adx_filter.py: this repo has no real
historical bid/ask spread feed, so every result so far used a *labelled
assumption* (10.0bps metals / 3.0bps CHFJPY / 1.5bps USDJPY, the "Realistic"
gold tier from scripts/research_gold_trend_pullback_atr.py, hand-picked for
the other two). This script quantifies how much that assumption actually
matters:

  1. Per-market breakeven spread (round-trip bps at which mean trade return
     crosses zero), OOS only (2023-2026 - the only period with a real edge;
     an IS breakeven number would be misleadingly reassuring low for a
     regime that lost money even cost-free) - both without and WITH the
     adx_min=25 filter chosen by the prior script's IS-only sweep.
  2. A spread sweep on the pooled OOS portfolio (with the chosen filter) to
     show how PF/Sharpe degrade as costs rise from the assumption toward the
     breakeven point, since a single "breakeven bps" number hides how
     quickly the edge decays approaching it.

Live-relevance: the bot never sees "spread_bps" directly - it pays whatever
the broker quotes at market-order time. This translates that into "how wide
could the real broker spread be before this stops paying" per market, which
is the actual demo-phase question this repo's role can help answer (per
CLAUDE.md: verify economics/robustness, no execution-code involvement).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import breakeven_spread_bps, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
CHOSEN_ADX_MIN = 25.0  # from research_mt5_trend_pullback_adx_filter.py's IS-only sweep

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]

SPREAD_SWEEP_BPS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}"
    )


def main():
    print("Loading 5 markets (cached from prior runs where available) ...")
    data = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = (df, spread_bps)
        print(f"  {label}: {len(df)} bars")

    print("\n" + "=" * 78)
    print("1. BREAKEVEN SPREAD (round-trip bps, OOS 2023-2026 only)")
    print("=" * 78)
    print(f"  {'Market':<8} {'Assumed':>8} {'Breakeven (no filter)':>24} {'Breakeven (adx_min=25)':>24}")
    oos_signaled_nofilter, oos_signaled_filtered = {}, {}
    for label, (df, spread_bps) in data.items():
        sig_nf = run_pipeline(df)
        oos_nf = sig_nf[sig_nf.index >= SPLIT]
        oos_signaled_nofilter[label] = (oos_nf, spread_bps)
        base_cfg = BacktestConfig(stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        be_nf = breakeven_spread_bps(oos_nf, base_cfg, lo=0.0, hi=100.0)

        sig_f = run_pipeline(df, adx_min=CHOSEN_ADX_MIN)
        oos_f = sig_f[sig_f.index >= SPLIT]
        oos_signaled_filtered[label] = (oos_f, spread_bps)
        be_f = breakeven_spread_bps(oos_f, base_cfg, lo=0.0, hi=100.0)

        print(f"  {label:<8} {spread_bps:>7.1f}bp {be_nf:>22.1f}bp {be_f:>22.1f}bp")

    print("\n" + "=" * 78)
    print("2. POOLED OOS PORTFOLIO: PF/Sharpe as spread rises (adx_min=25 filter)")
    print("=" * 78)
    full_index_cache = {}
    for label, (oos_f, _) in oos_signaled_filtered.items():
        full_index_cache[label] = oos_f.index
    span_start = min(idx.min() for idx in full_index_cache.values())
    span_end = max(idx.max() for idx in full_index_cache.values())
    full_index = pd.date_range(span_start, span_end, freq="D")

    for test_bps in SPREAD_SWEEP_BPS:
        trades_by_market = {}
        for label, (oos_f, _) in oos_signaled_filtered.items():
            cfg = BacktestConfig(spread_bps=test_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades_by_market[label] = simulate_trades(oos_f, cfg)
        pooled = pd.concat(trades_by_market.values(), ignore_index=True)
        s = summarize(pooled, full_index)
        print(f"  spread={test_bps:>5.1f}bp  {fmt(s)}")

    print("\n" + "=" * 78)
    print("3. REFERENCE: same sweep with each market's ASSUMED spread as the floor")
    print("=" * 78)
    print("  (i.e. how much headroom exists between the assumption used elsewhere")
    print("   in this research and each market's actual OOS breakeven, filtered)")
    for label, (oos_f, spread_bps) in oos_signaled_filtered.items():
        base_cfg = BacktestConfig(stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        be_f = breakeven_spread_bps(oos_f, base_cfg, lo=0.0, hi=100.0)
        headroom = be_f - spread_bps
        flag = "OK" if headroom > spread_bps else ("THIN" if headroom > 0 else "NEGATIVE")
        print(f"  {label:<8} assumed={spread_bps:>5.1f}bp  breakeven={be_f:>6.1f}bp  headroom={headroom:>6.1f}bp  [{flag}]")


if __name__ == "__main__":
    main()
