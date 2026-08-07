"""Genuine out-of-sample check for the max_total_risk_pct finding from
sweep_risk_caps.py (0.125 beat the 0.15 locked-config default on Sharpe+Calmar+MDD
simultaneously, in-sample 2018-2024) -- same discipline as oos_holdout_trailing.py:
fresh data through today, tested only on 2025-today, a window untouched by any
sweep. Also tests 0.025 (2.5%), matching the live OU-Modell-MT5-Bridge bot's actual
max_total_risk_pct on Konto 2 (see config.py there) -- i.e. "what if the live bot's
own aggregate-risk cap were applied to this backtest engine".

One fresh download pass, several max_total_risk_pct values run against it (cheaper
than oos_holdout_trailing.py's per-variant re-download)."""

import sys
import time

import pandas as pd
import yfinance as yf

import config
import metrics
import portfolio

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
CAPS_TO_TEST = [0.15, 0.125, 0.025]


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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}")

    rows = []
    for cap in CAPS_TO_TEST:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=None,
            be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
            max_total_risk_pct=cap,
        )
        m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
        rows.append({"variant": f"max_total_risk_pct={cap}", **m, "final_equity": eq.iloc[-1]})
        print(f"  cap={cap}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
              f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.0f}% "
              f"trades={m['n_trades']} ({time.time()-t0:.1f}s)")
        eq.loc[HOLDOUT_START:today].to_frame("equity").to_csv(
            config.RESULTS_DIR / universe_key / f"holdout_2025_equity_cap{cap}.csv"
        )

    bench_eq = 100_000.0 * (benchmark.loc[HOLDOUT_START:today] / benchmark.loc[HOLDOUT_START:today].iloc[0])
    m3 = metrics.summarize(bench_eq.pct_change().fillna(0.0))
    rows.append({"variant": "buy_and_hold", **m3, "final_equity": bench_eq.iloc[-1]})
    print(f"  buy_and_hold: sharpe={m3['sharpe']:.2f}")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_riskcap_comparison.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
