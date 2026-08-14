"""Follow-up to the regime-shift and proven-filters passes: tests whether
dropping individual markets from the 5-market portfolio improves the OVERALL
combined result (leave-one-out), and specifically whether removing PLATINUM
and applying the Gold-confirms-Silver alignment filter to Silver
(scripts/research_mt5_trend_pullback_proven_filters.py found this helped
Silver on its own: OOS PF 1.347->1.530, Sharpe 0.47->0.65) improves the
portfolio as a whole.

All variants use the bot's default config (EMA150/RSI14x35/ATR14x2.0/RR2.0,
no ADX filter - kept out here to isolate the market-composition question;
combining ADX + dropout + alignment at once would confound which change
caused what) on the regime-shifted new IS (2023-01->2024-07) / new OOS
(2024-07->2026-08) window, both as pooled price-return metrics (Sharpe/PF/
CAGR/MaxDD) and as a $100k / 1%-risk / max-3-concurrent dollar account
simulation (mt5_trend_pullback/account_simulation.py) - the two can move
differently since the account sim also reflects HOW OFTEN the 3-concurrent-
position cap binds, which changes when a market is removed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.account_simulation import account_stats, simulate_account
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")

STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01
MAX_CONCURRENT = 3
ALIGNMENT_WINDOW = 5

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def combined(trades_by_market: dict, index_by_market: dict) -> dict:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    if not starts:
        return summarize(combined_trades, pd.DatetimeIndex([]))
    full_index = pd.date_range(min(starts), max(ends), freq="D")
    return summarize(combined_trades, full_index)


def alignment_filter(trades: pd.DataFrame, partner_close_d1: pd.Series, window: int = ALIGNMENT_WINDOW) -> pd.DataFrame:
    import numpy as np
    if trades.empty:
        return trades
    chg = partner_close_d1.sort_index().pct_change(window)
    entry_dates = trades["entry_time"].dt.tz_localize(None).dt.normalize()
    s_sorted = chg.dropna().sort_index()
    idx = s_sorted.index.searchsorted(entry_dates.to_numpy(), side="left") - 1
    idx_clipped = idx.clip(min=0)
    values = s_sorted.to_numpy()[idx_clipped]
    values = pd.Series(values, index=trades.index, dtype=float)
    values[idx < 0] = np.nan
    out = trades.copy()
    out["partner_chg"] = values
    out = out.dropna(subset=["partner_chg"])
    return out[out["partner_chg"] > 0]


def account_line(trades_by_market: dict) -> str:
    sim = simulate_account(trades_by_market, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
    s = account_stats(sim, starting_equity=STARTING_EQUITY)
    return (f"n_taken={s['n_trades']:>4} (uebersprungen {s['n_skipped']:>3})  "
            f"Endkapital=${s['final_equity']:>11,.0f}  Return={s['total_return']:+.1%}  "
            f"MaxDD={s['max_drawdown_pct']:+.1%} (${s['max_drawdown_usd']:,.0f})")


def main():
    trades_oos, idx_oos = {}, {}
    d1_close = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
        trades = simulate_trades(signaled, cfg)
        oos_t = trades[trades["entry_time"] >= NEW_SPLIT]
        oos_idx = signaled.index[signaled.index >= NEW_SPLIT]
        trades_oos[label] = oos_t
        idx_oos[label] = oos_idx

        d1 = fetch_timeframe(key, "D1", DATA_START, DATA_END)
        close = d1["Close"]
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        d1_close[key] = close

    labels = [label for _, _, label, _ in MARKETS]

    print("=" * 100)
    print("0. BASELINE -- all 5 markets, bot default config, new OOS (2024-07 -> 2026-08)")
    print("=" * 100)
    base_pooled = combined(trades_oos, idx_oos)
    print(f"  Pooled (return-based): {fmt(base_pooled)}")
    print(f"  Account ($100k, 1% risk, max 3 concurrent): {account_line(trades_oos)}")

    print("\n" + "=" * 100)
    print("1. LEAVE-ONE-OUT -- drop each market individually, rest at bot default")
    print("=" * 100)
    for drop_label in labels:
        subset_trades = {k: v for k, v in trades_oos.items() if k != drop_label}
        subset_idx = {k: v for k, v in idx_oos.items() if k != drop_label}
        s = combined(subset_trades, subset_idx)
        arrow_pf = "UP" if s["profit_factor"] > base_pooled["profit_factor"] else "DOWN"
        arrow_sh = "UP" if s["sharpe"] > base_pooled["sharpe"] else "DOWN"
        print(f"\n  Without {drop_label}:")
        print(f"    Pooled : {fmt(s)}   (PF {arrow_pf}, Sharpe {arrow_sh})")
        print(f"    Account: {account_line(subset_trades)}")

    print("\n" + "=" * 100)
    print("2. PLATINUM REMOVED + GOLD-CONFIRMS-SILVER ALIGNMENT FILTER ON SILVER")
    print("=" * 100)
    silver_aligned = alignment_filter(trades_oos["XAGUSD"], d1_close["GOLD"])

    variant_no_platinum_no_filter = {k: v for k, v in trades_oos.items() if k != "XPTUSD"}
    variant_no_platinum_no_filter_idx = {k: v for k, v in idx_oos.items() if k != "XPTUSD"}
    s_a = combined(variant_no_platinum_no_filter, variant_no_platinum_no_filter_idx)
    print("\n  2a. No Platinum, no filter (Gold/Silver/CHFJPY/USDJPY, baseline):")
    print(f"    Pooled : {fmt(s_a)}")
    print(f"    Account: {account_line(variant_no_platinum_no_filter)}")

    variant_no_platinum_aligned = dict(variant_no_platinum_no_filter)
    variant_no_platinum_aligned["XAGUSD"] = silver_aligned
    variant_no_platinum_aligned_idx = dict(variant_no_platinum_no_filter_idx)  # index spans unaffected by trade filtering
    s_b = combined(variant_no_platinum_aligned, variant_no_platinum_aligned_idx)
    print("\n  2b. No Platinum + Silver filtered by Gold-alignment:")
    print(f"    Pooled : {fmt(s_b)}")
    print(f"    Account: {account_line(variant_no_platinum_aligned)}")

    print("\n  For reference -- Silver alone, filtered vs not:")
    print(f"    Silver baseline : {fmt(summarize(trades_oos['XAGUSD'], idx_oos['XAGUSD']))}")
    print(f"    Silver +aligned : {fmt(summarize(silver_aligned, idx_oos['XAGUSD']))}")

    print("\n" + "=" * 100)
    print("3. SUMMARY TABLE")
    print("=" * 100)
    rows = [
        ("Full 5-market baseline", base_pooled, trades_oos),
        ("No Platinum", s_a, variant_no_platinum_no_filter),
        ("No Platinum + Silver-aligned", s_b, variant_no_platinum_aligned),
    ]
    for name, s, tbm in rows:
        sim = simulate_account(tbm, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
        acc = account_stats(sim, starting_equity=STARTING_EQUITY)
        print(f"  {name:<32} PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  "
              f"CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}   |   "
              f"$ Endkapital={acc['final_equity']:,.0f}  Return={acc['total_return']:+.1%}  "
              f"MaxDD$={acc['max_drawdown_pct']:+.1%}")


if __name__ == "__main__":
    main()
