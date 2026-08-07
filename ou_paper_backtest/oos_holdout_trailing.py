"""Genuine out-of-sample check for the trailing-stop variant (portfolio.
simulate_trailing_bracket_portfolio), mirroring the existing 2025+ holdout test for
the locked fixed-CRV bracket (see app_pages/fertige_strategien.py's "Out-of-Sample"
tab / results/<market>/holdout_2025_equity_riskbased.csv) -- same discipline: fresh
data downloaded straight from yfinance (NOT the cached _panel.parquet, which was
built with config.DOWNLOAD_END frozen at 2024-12-31 and would silently return stale
data for anything past that), tested only on 2025-today, a window that never
appeared in ANY sweep (sweep_trailing.py's baseline/trail comparison and the whole
in-sample OU-selection both stop at 2024-12-31).

Downloads fresh instead of reusing sweep_trailing.py's cached panel/ATR data for the
same reason the original holdout test did: the cache is frozen at 2024-12-31 and
would just replay in-sample-adjacent data under a different date label.

Recomputes BOTH the fixed baseline and the trailing variant on the exact same fresh
download, in the same run, so the comparison is apples-to-apples (not diffed against
a baseline CSV that may have been downloaded on a different day)."""

import sys
import time

import pandas as pd
import yfinance as yf

import config
import metrics
import portfolio

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"  # ~1yr lookback so 200d EMA regime filter + 20d BB are warm by 2025-01-01


def _download_fresh(tickers: list[str]) -> pd.DataFrame:
    series = {}
    for i, t in enumerate(tickers):
        df = yf.download(t, start=DOWNLOAD_START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            print(f"  [{i+1}/{len(tickers)}] {t}: no data, skipped")
            continue
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        series[t] = close.dropna()
        print(f"  [{i+1}/{len(tickers)}] {t}: ok ({close.index.min().date()} - {close.index.max().date()})")
    return pd.DataFrame(series).sort_index()


def run(universe_key: str, trail_mult: float = 3.0) -> pd.DataFrame:
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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today} (never used in any sweep)")

    rows = []

    t0 = time.time()
    eq_base, tr_base = portfolio.simulate_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=None,
        be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
    )
    m = metrics.summarize(eq_base.pct_change().fillna(0.0), tr_base)
    rows.append({"variant": "baseline_fixed_3sigma", **m, "final_equity": eq_base.iloc[-1]})
    print(f"  baseline_fixed: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
          f"mdd={m['max_drawdown_pct']:.1f}% trades={m['n_trades']} ({time.time()-t0:.1f}s)")

    t0 = time.time()
    eq_trail, tr_trail = portfolio.simulate_trailing_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today, trail_type="stddev", trail_mult=trail_mult,
        regime_filter=regime,
    )
    m2 = metrics.summarize(eq_trail.pct_change().fillna(0.0), tr_trail)
    rows.append({"variant": f"trail_stddev_{trail_mult}", **m2, "final_equity": eq_trail.iloc[-1]})
    print(f"  trail_stddev({trail_mult}): sharpe={m2['sharpe']:.2f} calmar={m2['calmar']:.2f} "
          f"mdd={m2['max_drawdown_pct']:.1f}% trades={m2['n_trades']} ({time.time()-t0:.1f}s)")

    bench_eq = 100_000.0 * (benchmark.loc[HOLDOUT_START:today] / benchmark.loc[HOLDOUT_START:today].iloc[0])
    m3 = metrics.summarize(bench_eq.pct_change().fillna(0.0))
    rows.append({"variant": "buy_and_hold", **m3, "final_equity": bench_eq.iloc[-1]})
    print(f"  buy_and_hold: sharpe={m3['sharpe']:.2f}")

    eq_base.loc[HOLDOUT_START:today].to_frame("equity").to_csv(
        config.RESULTS_DIR / universe_key / "holdout_2025_equity_baseline_recheck.csv"
    )
    eq_trail.loc[HOLDOUT_START:today].to_frame("equity").to_csv(
        config.RESULTS_DIR / universe_key / f"holdout_2025_equity_trail_stddev{trail_mult}.csv"
    )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    trail_mult = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    df = run(universe_key, trail_mult)
    out_path = config.RESULTS_DIR / universe_key / f"oos_holdout_trailing_comparison.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
