"""Portfolio-level profit-lock exit vs. the locked live "Funded Challenge" config
-- requested (2026-08-10) after the user observed ~2% aggregate open floating
profit last week that later decayed back toward breakeven on several positions
(via the breakeven-stop move) before any single trade reached its own 1:1.5 TP.
Question: would flattening ALL open positions once aggregate unrealized profit
hits X% of equity (then waiting for fresh signals) reach the 10% funded-challenge
target faster than the current per-trade TP rule?

Locked baseline entry/exit throughout (established in oos_holdout_be_sweep.py /
oos_holdout_035_3.py, live on Konto 2 since 2026-08-07): stop_sigma=3.0,
rr_ratio=1.5, be_trigger_r=0.35, risk_pct=0.25%, max_total_risk_pct=5%.
Same genuine 2025+ S&P holdout (fresh data, never touched by any sweep), same
funded-challenge rule checks (max 3% single-day loss, 10% profit target) as
every other script in this series.

Variants:
  A) baseline_tp1.5_no_lock: today's exact live rule, no change -- reference point.
  B) no_tp_no_lock: TP removed, no portfolio lock -- isolates the effect of
     just removing the per-trade TP, before adding the new rule on top.
  C) tp1.5_plus_lock_2pct: keeps the per-trade TP AND adds the portfolio lock
     on top (whichever fires first) -- the "stack, don't replace" variant.
  D-G) no_tp_lock_{1,1.5,2,3}pct: TP fully REPLACED by the portfolio lock at
     four threshold levels -- D-G brackets the user's exact ask (2%, i.e. G).

First run (2026-08-10) found ALL full-flatten variants (close_frac=1.0, i.e.
close every open position entirely once the lock fires) underperformed the
plain per-trade TP baseline -- flattening everything cuts off the occasional
big winner along with the small ones. Follow-up (2026-08-11) asks: what if
only a FRACTION of each position is closed when the lock fires, instead of
all of it? Added partial-close variants at the two best full-close thresholds
(1% and 2%) and close_frac in [0.25, 0.5, 0.75] -- trims every open position
down to (1 - close_frac) of its size, realizing part of the gain while
leaving the rest running under its normal stop/BE/TP.
"""

import sys
import time

import pandas as pd
import yfinance as yf

import config
import metrics
import portfolio

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
DAILY_LOSS_LIMIT_PCT = -3.0

STOP_SIGMA = 3.0
BE_TRIGGER_R = 0.35
RISK_PCT = 0.0025
MAX_TOTAL_RISK_PCT = 0.05

# (label, rr_ratio, portfolio_profit_lock_pct, close_frac, n_best)
VARIANTS = [
    ("baseline_tp1.5_no_lock", 1.5, None, 1.0, None),
    ("no_tp_no_lock", None, None, 1.0, None),
    ("tp1.5_plus_lock_2pct", 1.5, 0.02, 1.0, None),
    ("no_tp_lock_1pct", None, 0.01, 1.0, None),
    ("no_tp_lock_1.5pct", None, 0.015, 1.0, None),
    ("no_tp_lock_2pct", None, 0.02, 1.0, None),
    ("no_tp_lock_3pct", None, 0.03, 1.0, None),
    # partial-close follow-up (2026-08-11): trim instead of flatten
    ("no_tp_lock_1pct_trim25", None, 0.01, 0.25, None),
    ("no_tp_lock_1pct_trim50", None, 0.01, 0.5, None),
    ("no_tp_lock_1pct_trim75", None, 0.01, 0.75, None),
    ("no_tp_lock_2pct_trim25", None, 0.02, 0.25, None),
    ("no_tp_lock_2pct_trim50", None, 0.02, 0.5, None),
    ("no_tp_lock_2pct_trim75", None, 0.02, 0.75, None),
    ("tp1.5_plus_lock_2pct_trim50", 1.5, 0.02, 0.5, None),
    # "close best N, TP stays active" follow-up (2026-08-11): TP is NOT replaced,
    # lock only skims the current best-N winners as an ADDITIONAL exit on top.
    ("tp1.5_plus_lock_2pct_best3", 1.5, 0.02, 1.0, 3),
    ("tp1.5_plus_lock_1pct_best3", 1.5, 0.01, 1.0, 3),
    ("tp1.5_plus_lock_2pct_best5", 1.5, 0.02, 1.0, 5),
]


def _download_fresh(tickers: list[str]) -> pd.DataFrame:
    series = {}
    for i, t in enumerate(tickers):
        df = yf.download(t, start=DOWNLOAD_START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            continue
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        series[t] = close.dropna()
    print(f"  downloaded {len(series)}/{len(tickers)} tickers")
    return pd.DataFrame(series).sort_index()


def run(universe_key: str) -> pd.DataFrame:
    ou_table = pd.read_csv(config.RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    tickers = sel.index.tolist()
    print(f"[{universe_key}] {len(tickers)} OU-selected tickers, downloading fresh through today...")
    panel = _download_fresh(tickers)

    bench_ticker = config.UNIVERSES[universe_key]["benchmark"]
    bench_df = yf.download(bench_ticker, start=DOWNLOAD_START, auto_adjust=True, progress=False)
    benchmark = bench_df["Close"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark.iloc[:, 0]
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)

    today = panel.index.max().date().isoformat()
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, 100k Startkapital, "
          f"SL={STOP_SIGMA}sigma, be_trigger_r={BE_TRIGGER_R}, "
          f"risk_pct={RISK_PCT}, cap={MAX_TOTAL_RISK_PCT}\n")

    rows = []
    for label, rr_ratio, lock_pct, close_frac, n_best in VARIANTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=STOP_SIGMA, rr_ratio=rr_ratio,
            be_trigger_r=BE_TRIGGER_R, allowed_directions=(1,), regime_filter=regime,
            risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
            portfolio_profit_lock_pct=lock_pct, portfolio_profit_lock_close_frac=close_frac,
            portfolio_profit_lock_n_best=n_best,
        )
        daily_ret = eq.pct_change().fillna(0.0)
        m = metrics.summarize(daily_ret, trades)
        worst_day_pct = daily_ret.min() * 100
        worst_day_date = daily_ret.idxmin()
        target_equity = eq.iloc[0] * 1.10
        hit = eq[eq >= target_equity]
        days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None
        breached = worst_day_pct < DAILY_LOSS_LIMIT_PCT
        n_lock_exits = sum(1 for tr in trades if tr["reason"] in ("portfolio_profit_lock", "portfolio_profit_lock_partial"))

        rows.append({
            "variant": label, "rr_ratio": rr_ratio, "profit_lock_pct": lock_pct,
            "close_frac": close_frac, "n_best": n_best,
            **m, "final_equity": eq.iloc[-1],
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "breached_3pct_daily_rule": breached, "days_to_10pct_target": days_to_10pct,
            "n_lock_exits": n_lock_exits,
        })
        print(f"  {label:24s}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
              f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.1f}% "
              f"worst_day={worst_day_pct:.2f}% 3%-Regel_verletzt={breached} "
              f"trades={m['n_trades']} (davon lock-exits={n_lock_exits}) "
              f"10%-Ziel_nach={days_to_10pct}_Tagen ({time.time()-t0:.1f}s)")

        eq.loc[HOLDOUT_START:today].to_frame("equity").to_csv(
            config.RESULTS_DIR / universe_key / f"holdout_2025_equity_profit_lock_{label}.csv"
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_profit_lock.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
