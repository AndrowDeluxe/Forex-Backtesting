"""Phase 6 re-run on David-V2's FULLY chained config from
scripts/research_mt5_david_v2_optimization.py (all 3 passes): trade_short=
True (unchanged), vol_window=1000, vol_quantile=0.7 (only trade the top 30%
of a market's own trailing normalized-ATR% distribution), rsi_oversold=30.0
(was 35.0), trend_len=200 (unchanged), stop_atr_mult=1.5/rr=2.0 (both
UNCHANGED bot defaults -- a Pass-2 stop/RR "optimization" and part of Pass 3's
RSI/trend_len grid were tested and REJECTED: IS Sharpe looked good but OOS
collapsed, the exact IS-good/OOS-bad overfitting pattern this repo's process
is designed to catch).

Same four checks, same periods, as scripts/research_mt5_david_v2_phase6.py
(which covered the bot-default config) so the two are directly comparable.

HEADLINE RESULT (2026-08-25): walk-forward at the TRADE level is now
positive in all 3 sub-periods (Sharpe +0.55/+0.61/+0.22, pooled) -- but the
Monte-Carlo section below, which simulates a real $100k portfolio at 0.5%
risk/trade with the bot's actual max_concurrent=3 cap, comes out NEGATIVE
on the most recent (most relevant) sub-period: real path ends at $90,857
(a loss), median Sharpe -0.39, P(MaxDD>10%)=78%. Trade-level pooled stats
(every trade treated as if fully capitalized independently) and portfolio-
level simulation (real sequential position sizing under the concurrency cap)
diverge sharply here, unlike Gold/Silber-Divergenz where they agreed --
David-V2's problem looks more like portfolio construction (4 correlated
markets sharing 3 slots) than pure entry-signal quality. NOT recommended
for live/demo deployment even after this full optimization pass -- see
knowledge/projects/mt5-david-v2-pullback.md for the complete writeup.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ou_paper_backtest"))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from gold_smc_htf_ltf.concurrent_backtest import equity_curve_to_daily_returns
from monte_carlo import run_monte_carlo
from mt5_david_v2.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from mt5_trend_pullback.account_simulation import simulate_account
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
PERIODS = [
    ("2016-2019", "2016-01-01", "2019-01-01"),
    ("2019-2022", "2019-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2026-08-01"),
]
MARKETS = [
    ("EURUSD", "H1", "EURUSD", 1.5),
    ("GBPUSD", "H1", "GBPUSD", 2.0),
    ("USDJPY", "H1", "USDJPY", 1.5),
    ("GOLD", "H4", "XAUUSD", 10.0),
]

STARTING_EQUITY = 100_000.0
RISK_PCT = 0.005  # config.py RISK_PERCENT default
MAX_CONCURRENT = 3

# Final chosen config (all 3 optimization passes chained)
VOL_WINDOW, VOL_QUANTILE = 1000, 0.7
RSI_OVERSOLD, TREND_LEN = 30.0, 200


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}"


def main():
    trades_by_market_full = {}
    signaled_by_market = {}
    for key, tf, label, spread_bps in MARKETS:
        print(f"Fetching {label} {tf} {DATA_START} -> {DATA_END} ...")
        df = fetch_timeframe(key, tf, DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df, rsi_oversold=RSI_OVERSOLD, trend_len=TREND_LEN, vol_window=VOL_WINDOW, vol_quantile=VOL_QUANTILE)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        trades_by_market_full[label] = trades
        signaled_by_market[label] = signaled

    # ================================================================ p6_1/p6_4
    print("\n" + "=" * 100)
    print("p6_1/p6_4 - WALK-FORWARD UEBER 3 ROLLIERENDE SUB-PERIODEN (finale Config, gepoolt)")
    print("=" * 100)
    for name, start, end in PERIODS:
        start_ts, end_ts = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        period_trades, period_idx = {}, {}
        for label, trades in trades_by_market_full.items():
            sig_idx = signaled_by_market[label].index
            period_idx[label] = sig_idx[(sig_idx >= start_ts) & (sig_idx < end_ts)]
            period_trades[label] = trades[(trades["entry_time"] >= start_ts) & (trades["entry_time"] < end_ts)]
        pooled_t = pd.concat(period_trades.values(), ignore_index=True)
        starts = [i.min() for i in period_idx.values() if len(i)]
        ends = [i.max() for i in period_idx.values() if len(i)]
        full_idx = pd.date_range(min(starts), max(ends), freq="D") if starts else pd.DatetimeIndex([])
        print(f"  {name:<10} {fmt(summarize(pooled_t, full_idx))}")
    print("  (Referenz Bot-Default, gepoolt ueber 4 Maerkte: deutlich negativ in allen 3 Perioden)")

    # ================================================================ p6_2
    print("\n" + "=" * 100)
    print(f"p6_2 - MONTE-CARLO-BOOTSTRAP (finale Config, Risk {RISK_PCT:.1%}/Trade, max {MAX_CONCURRENT} gleichzeitige Positionen)")
    print("=" * 100)
    recent_start = pd.Timestamp("2022-01-01", tz="UTC")
    trades_recent = {label: t[t["entry_time"] >= recent_start] for label, t in trades_by_market_full.items()}
    full_index = None
    for label, sig in signaled_by_market.items():
        idx = sig.index[sig.index >= recent_start]
        full_index = idx if full_index is None else full_index.union(idx)

    sim = simulate_account(trades_recent, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
    daily = equity_curve_to_daily_returns(sim["equity_curve"], full_index)
    mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    print(f"Sub-Periode 2022-2026, real path: n_taken={sim['n_taken']}, n_skipped={sim['n_skipped']}, final_equity={sim['final_equity']:,.0f}")
    for p in (5, 25, 50, 75, 95):
        dd_p = np.percentile(s["max_drawdown_pct"], p)
        ret_p = np.percentile(s["total_return_pct"], p)
        print(f"  P{p:>2}  MaxDD={dd_p:>8.2f}%   TotalReturn={ret_p:>+9.2f}%")
    for limit in (0.10, 0.20, 0.30):
        breach = (s["max_drawdown_pct"] < -limit * 100).mean()
        print(f"  P(MaxDD > {limit:.0%}) = {breach:.1%}", end="   ")
    print(f"\n  Median Sharpe={np.nanmedian(s['sharpe']):.2f}   Median Calmar={np.nanmedian(s['calmar']):.2f}")
    print("  (Referenz Bot-Default gleiche Periode: P(MaxDD>30%)=79.8%, Median Sharpe=-0.51)")

    # ================================================================ p6_3
    print("\n" + "=" * 100)
    print("p6_3 - KOSTEN-SENSITIVITAET (letzte Sub-Periode 2022-2026, je Markt, finale Config)")
    print("=" * 100)
    spread_candidates = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0]
    for key, tf, label, assumed_bps in MARKETS:
        sig = signaled_by_market[label]
        sig_recent = sig[sig.index >= recent_start]
        print(f"\n{label} (angenommen: {assumed_bps}bps):")
        breakeven = None
        for sp in spread_candidates:
            cfg = BacktestConfig(spread_bps=sp, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            t = simulate_trades(sig_recent, cfg)
            if t.empty:
                print(f"  spread={sp:>6.1f}bps  n=0")
                continue
            total_ret = (1 + t["return_pct"]).prod() - 1
            pf = t.loc[t["return_pct"] > 0, "return_pct"].sum() / -t.loc[t["return_pct"] < 0, "return_pct"].sum() if (t["return_pct"] < 0).any() else float("inf")
            print(f"  spread={sp:>6.1f}bps  n={len(t):>3}  TotalReturn={total_ret:>+8.2%}  PF={pf:.3f}")
            if breakeven is None and total_ret < 0:
                breakeven = sp
        if breakeven:
            prior = spread_candidates[spread_candidates.index(breakeven) - 1] if spread_candidates.index(breakeven) > 0 else 0.0
            print(f"  -> Breakeven-Spread zwischen {prior:.1f} und {breakeven:.1f} bps (Sicherheitsfaktor vs. Annahme {assumed_bps}bps: {breakeven / assumed_bps:.1f}x)")
        else:
            print(f"  -> bleibt profitabel im gesamten getesteten Bereich")


if __name__ == "__main__":
    main()
