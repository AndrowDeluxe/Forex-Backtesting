"""Research script: replicate Vojtko & Dujava's (2026) weekly dual-momentum
rotation between Gold and Bitcoin on our own repo's real data - Gold via the
existing Dukascopy XAUUSD feed, Bitcoin via the existing Binance BTCUSDT
feed (see gold_bitcoin_dual_momentum/data.py for the disclosed ETF-vs-spot
data deviation from the paper).

Structurally this candidate has nothing to do with the Gold ASB engine - no
attempt is made to combine it with asian_range_breakout. It's evaluated
purely on its own merits as a standalone weekly rotation strategy, following
this repo's own honest-findings discipline (parameter sweep -> IS/OOS split)
even though the original paper doesn't include an IS/OOS check itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_bitcoin_dual_momentum.data import fetch_weekly_gold_btc
from gold_bitcoin_dual_momentum.engine import simulate_dual_momentum

START, END = "2017-08-20", "2026-07-29"
LOOKBACKS = [1, 2, 3, 4, 6, 8, 12, 20, 24, 28]
COMPOSITE_SET = [4, 8, 12]
WARMUP_WEEKS = 40  # max(lookback=28, vol_lookback=12) + buffer, applied uniformly across all sweeps
VOL_CAP = 0.20
SPLIT_FRACTION = 0.7  # IS/OOS split point for the recommended (vol-capped composite) variant


def perf_metrics(weekly_returns: pd.Series) -> dict:
    r = weekly_returns.dropna()
    if len(r) == 0:
        return {"ann_return": float("nan"), "ann_vol": float("nan"), "sharpe": float("nan"), "max_dd": float("nan"), "calmar": float("nan"), "hit_rate": float("nan"), "n_weeks": 0}
    n_years = len(r) / 52
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1
    ann_vol = r.std() * np.sqrt(52)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float("nan")
    equity = (1 + r).cumprod()
    max_dd = (equity / equity.cummax() - 1).min()
    calmar = ann_return / abs(max_dd) if max_dd < 0 else float("nan")
    hit_rate = (r > 0).mean()
    return {"ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe, "max_dd": max_dd, "calmar": calmar, "hit_rate": hit_rate, "n_weeks": len(r)}


def fmt(m: dict) -> str:
    return (
        f"Return={m['ann_return']:+.2%}  Vol={m['ann_vol']:.2%}  Sharpe={m['sharpe']:.2f}  "
        f"MaxDD={m['max_dd']:.2%}  Calmar={m['calmar']:.2f}  Hit={m['hit_rate']:.1%}  n={m['n_weeks']}"
    )


def main():
    print(f"Fetching weekly GOLD/BTC {START} -> {END} ...")
    weekly = fetch_weekly_gold_btc(START, END)
    print(f"{len(weekly)} weekly bars ({weekly.index[0].date()} -> {weekly.index[-1].date()})")

    print("\n" + "=" * 78)
    print("1. PURE DUAL MOMENTUM (no vol cap)")
    print("=" * 78)
    pure_returns = {}
    for lb in LOOKBACKS:
        sim = simulate_dual_momentum(weekly, lookback_weeks=lb, vol_cap=None)
        r = sim["strategy_return"].iloc[WARMUP_WEEKS:]
        pure_returns[lb] = r
        print(f"  X={lb:>2}w  {fmt(perf_metrics(r))}")
    composite_pure = pd.concat([pure_returns[lb] for lb in COMPOSITE_SET], axis=1).mean(axis=1)
    print(f"  Composite (4/8/12w avg)  {fmt(perf_metrics(composite_pure))}")

    print("\n" + "=" * 78)
    print(f"2. VOLATILITY-CAPPED DUAL MOMENTUM (cap={VOL_CAP:.0%} annualized)")
    print("=" * 78)
    capped_returns = {}
    for lb in LOOKBACKS:
        sim = simulate_dual_momentum(weekly, lookback_weeks=lb, vol_cap=VOL_CAP)
        r = sim["strategy_return"].iloc[WARMUP_WEEKS:]
        capped_returns[lb] = r
        print(f"  X={lb:>2}w  {fmt(perf_metrics(r))}")
    composite_capped = pd.concat([capped_returns[lb] for lb in COMPOSITE_SET], axis=1).mean(axis=1)
    print(f"  Composite (4/8/12w avg)  {fmt(perf_metrics(composite_capped))}")

    print("\n" + "=" * 78)
    print("3. IS/OOS CHECK on the vol-capped composite (not in the original paper)")
    print("=" * 78)
    split_idx = int(len(composite_capped) * SPLIT_FRACTION)
    is_ret = composite_capped.iloc[:split_idx]
    oos_ret = composite_capped.iloc[split_idx:]
    print(f"  Full: {fmt(perf_metrics(composite_capped))}")
    print(f"  IS  : {fmt(perf_metrics(is_ret))}  ({is_ret.index[0].date()} -> {is_ret.index[-1].date()})")
    print(f"  OOS : {fmt(perf_metrics(oos_ret))}  ({oos_ret.index[0].date()} -> {oos_ret.index[-1].date()})")

    print(
        "\nNote: buy-and-hold Bitcoin over this window is a very high bar (BTC's own multi-year bull run\n"
        "dominates most rotation strategies in-sample) - the IS/OOS split above is the honesty check on\n"
        "whether the momentum-switching rule itself, not just broad BTC exposure, is doing the work."
    )


if __name__ == "__main__":
    main()
