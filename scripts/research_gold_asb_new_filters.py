"""Tests three filter ideas (flagged as "noch offen/ungetestet" against the
Gold ASB in an earlier session) against the CURRENT production configuration
(Execution-Overlay entry + ADX + Trend-Bias + Entry-Delay + Silver-Alignment,
see asian_range_breakout/execution_overlay.py + walkforward.py):

1. Cross-Pair-Confirmation (reused from strategy/cls_advanced.py): that
   module found the cross-pair check itself real (confirmed days do show a
   higher persistence rate) but not monetizable as ITS OWN entry trigger.
   Translated here as a REGIME filter, not a new rule: was the PRIOR Berlin
   calendar day's FX-majors 06:00-09:00 move a broad, multi-pair-confirmed
   dollar move, or an isolated single-pair move? No lookahead - only the
   prior day's already-closed session is used, looked up before Gold's own
   Asian range (21:00-01:00 NY) begins.

2. Jump-Activity (generic bipower-variation jump ratio - NOT a literal
   replication of "Hizmeri et al.", which isn't available in this repo/
   session; this is the standard Barndorff-Nielsen & Shephard-style
   realized-variance/bipower-variation jump decomposition, serving the same
   "how much of today's variance came from a few large jumps vs. smooth
   diffusion" purpose). Computed over the PRIOR calendar day's Gold M15
   bars, again no lookahead.

3. LVN/HVN Volume Profile (reused from auction_playbook/indicators.py):
   classifies the price bin adjacent to the breakout level (top bin for a
   long/range_high breakout, bottom bin for a short/range_low breakout)
   using THIS window's own volume profile (fully known the instant the
   window closes and the order is armed - no lookahead). Hypothesis: a
   breakout through/near a Low-Volume-Node (thin prior trading, "air
   pocket") should run better than one right next to a High-Volume-Node
   (heavily-traded congestion just under the level = absorption risk).
   Uses Dukascopy's own Gold "volume" column, a broker-side tick-count
   proxy, NOT real exchange order flow - same disclosed caveat as
   auction_playbook's own SP500/NASDAQ Dukascopy volume.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.execution_overlay import simulate_asian_breakout_overlay
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
)
from auction_playbook.indicators import volume_profile
from combined_strategy.data import fetch_timeframe
from strategy.cls_advanced import PAIRS, compute_cross_confirmation, compute_daily_features, to_berlin
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def production_trades(df, daily_close_gold, daily_close_silver):
    t = simulate_asian_breakout_overlay(df)
    t = apply_adx_filter(t, adx_min=15)
    t = apply_trend_bias_filter(t, daily_close_gold, sma_window=200)
    t = apply_entry_delay_filter(t, max_delay_bars=3)
    t = apply_silver_alignment_filter(t, daily_close_silver, window=5)
    return t.sort_values("entry_time").reset_index(drop=True)


def bucket_report(trades: pd.DataFrame, bucket_col: str, label: str):
    print(f"\n  {label}")
    for b, g in trades.groupby(bucket_col, observed=True):
        print(f"    {b!s:<12} {fmt(trade_stats(g))}")
    is_t = trades[trades["entry_time"] < SPLIT]
    oos_t = trades[trades["entry_time"] >= SPLIT]
    print(f"    IS : {fmt(trade_stats(is_t))}   OOS: {fmt(trade_stats(oos_t))}")


# =============================================================================
# 1. Cross-Pair-Confirmation regime filter
# =============================================================================
def attach_cross_pair_regime(trades: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    print("Fetching 6 FX majors M15 for cross-pair confirmation...")
    daily_by_pair = {}
    for pair in PAIRS:
        px = fetch_timeframe(pair, "M15", start, end)
        px = px.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
        daily_by_pair[pair] = compute_daily_features(px)

    confirm = compute_cross_confirmation(daily_by_pair)
    confirm_df = pd.DataFrame(confirm)  # index: date, columns: pairs, values: bool
    n_confirmed = confirm_df.sum(axis=1)
    n_total = confirm_df.count(axis=1)
    broad_day = (n_confirmed / n_total) >= 0.5  # majority of majors confirmed -> "broad dollar day"

    out = trades.copy()
    berlin_window_start = to_berlin(pd.DatetimeIndex(out["window_start"]))
    lookup_date = (berlin_window_start - pd.Timedelta(days=1)).date  # PRIOR Berlin calendar day, no lookahead
    out["prior_day_broad_move"] = pd.Series(lookup_date, index=out.index).map(broad_day)
    out["regime_cross_pair"] = out["prior_day_broad_move"].map({True: "broad", False: "isolated"})
    return out


# =============================================================================
# 2. Jump-Activity (bipower variation) regime filter
# =============================================================================
def compute_daily_jump_ratio(df: pd.DataFrame) -> pd.Series:
    """One value per NY calendar day: RJ = (RV - BV) / RV, the fraction of
    that day's M15 realized variance attributable to jumps (RV = sum of
    squared log-returns, BV = scaled bipower variation using consecutive
    |return| products - the standard jump-robust variance estimator).
    RJ near 0 = smooth/diffusive day, RJ closer to 1 = jump-dominated day."""
    r = np.log(df["close"]).diff()
    day = df.index.date
    rows = []
    for d, idx in pd.Series(r.index, index=day).groupby(level=0):
        ret = r.loc[idx].dropna()
        if len(ret) < 5:
            continue
        rv = (ret ** 2).sum()
        bv = (np.pi / 2) * (ret.abs().to_numpy()[1:] * ret.abs().to_numpy()[:-1]).sum()
        rj = max(0.0, (rv - bv) / rv) if rv > 0 else np.nan
        rows.append({"date": d, "jump_ratio": rj})
    return pd.DataFrame(rows).set_index("date")["jump_ratio"]


def attach_jump_regime(trades: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    jr = compute_daily_jump_ratio(df)
    out = trades.copy()
    lookup_date = (out["window_start"] - pd.Timedelta(days=1)).dt.date  # PRIOR NY calendar day
    out["prior_day_jump_ratio"] = pd.Series(lookup_date, index=out.index).map(jr)
    valid = out["prior_day_jump_ratio"].dropna()
    if valid.empty:
        out["regime_jump"] = pd.NA
        return out
    terciles = valid.quantile([1 / 3, 2 / 3])
    out["regime_jump"] = pd.cut(
        out["prior_day_jump_ratio"],
        bins=[-np.inf, terciles.iloc[0], terciles.iloc[1], np.inf],
        labels=["low_jump", "mid_jump", "high_jump"],
    )
    return out


# =============================================================================
# 3. LVN/HVN Volume Profile filter
# =============================================================================
def attach_volume_profile_regime(trades: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    levels = []
    for _, tr in trades.iterrows():
        window = df.loc[tr["window_start"]: tr["window_end"]]
        window = window.iloc[:-1] if len(window) > 1 else window  # window_end bar itself is outside the range
        profile = volume_profile(window, num_bins=8)
        if profile.empty:
            levels.append(pd.NA)
            continue
        edge_bin = profile.iloc[-1] if tr["direction"] == "long" else profile.iloc[0]
        levels.append(edge_bin["level"])
    out = trades.copy()
    out["regime_volprofile"] = levels
    return out


def main():
    print(f"Fetching GOLD/SILVER M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    print("Simulating production trades (Overlay + ADX + Trend + Delay + Silver)...")
    trades = production_trades(df, daily_close_gold, daily_close_silver)
    baseline = trade_stats(trades)
    print(f"\nBaseline (current production, no new filter): {fmt(baseline)}")

    print("\n" + "=" * 78)
    print("1. CROSS-PAIR-CONFIRMATION REGIME (prior Berlin day, broad vs. isolated FX move)")
    print("=" * 78)
    t1 = attach_cross_pair_regime(trades, START, END)
    bucket_report(t1, "regime_cross_pair", "Bucket-Vergleich")

    print("\n" + "=" * 78)
    print("2. JUMP-ACTIVITY REGIME (prior NY day, bipower-variation jump ratio terciles)")
    print("=" * 78)
    t2 = attach_jump_regime(trades, df)
    bucket_report(t2, "regime_jump", "Bucket-Vergleich")

    print("\n" + "=" * 78)
    print("3. LVN/HVN VOLUME PROFILE (this window's own profile, bin adjacent to breakout level)")
    print("=" * 78)
    t3 = attach_volume_profile_regime(trades, df)
    bucket_report(t3, "regime_volprofile", "Bucket-Vergleich")

    print(
        "\nHinweis: alle drei sind Bucket-Vergleiche auf der VOLLEN Historie + IS/OOS-Split, "
        "kein volles Walk-Forward - das waere der naechste Schritt fuer jeden Kandidaten, der "
        "hier tatsaechlich eine konsistente, nicht Ausreisser-getriebene Trennung zeigt."
    )


if __name__ == "__main__":
    main()
