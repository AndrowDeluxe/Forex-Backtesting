"""Main orchestration: replicate the paper's BBfull vs BBOU vs benchmark comparison,
for either universe (S&P 500 sample or Nasdaq-100), including a $100k risk-based
equity curve (portfolio.py) on top of the paper's own %-return comparison.

1. Load cached price panel (built by data.py) for the given universe.
2. Estimate OU parameters in-sample (2010-2017) and select the OU-universe.
3. Backtest BBfull (all tickers) and BBOU (OU-selected only) out-of-sample (2018-2024),
   both as %-return portfolios (paper-style) and as a $100k account equity curve.
4. Compare against the universe's benchmark index.
5. Save metrics + equity curves + plots to results/<universe>/.
"""

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

import bollinger
import config
import metrics
import ou_model
import portfolio


def load_panel(universe_key: str) -> pd.DataFrame:
    suffix = "" if universe_key == "sp500" else f"_{universe_key}"
    path = config.DATA_CACHE / f"_panel{suffix}.parquet"
    return pd.read_parquet(path)


def load_benchmark(universe_key: str) -> pd.Series:
    ticker = config.UNIVERSES[universe_key]["benchmark"]
    safe = ticker.replace("^", "IDX_")
    path = config.DATA_CACHE / f"{safe}.parquet"
    if path.exists():
        s = pd.read_parquet(path).iloc[:, 0]
    else:
        s = yf.download(ticker, start=config.DOWNLOAD_START, end=config.DOWNLOAD_END,
                         auto_adjust=True, progress=False)["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s.to_frame().to_parquet(path)
    s.name = "benchmark"
    return s


def run_pipeline(universe_key: str):
    out_dir = config.RESULTS_DIR / universe_key
    out_dir.mkdir(parents=True, exist_ok=True)

    panel = load_panel(universe_key)
    benchmark = load_benchmark(universe_key)
    label = config.UNIVERSES[universe_key]["label"]
    bench_label = config.UNIVERSES[universe_key]["benchmark_label"]
    print(f"\n{'='*70}\n{label}\n{'='*70}")
    print(f"Universe panel: {panel.shape[1]} tickers, {panel.shape[0]} rows "
          f"({panel.index.min().date()} - {panel.index.max().date()})")

    # --- 1. In-sample OU estimation & selection ---
    print("\nEstimating OU parameters in-sample (2010-2017)...")
    ou_table = ou_model.build_ou_summary_table(panel, config.IN_SAMPLE_START, config.IN_SAMPLE_END)
    ou_table.to_csv(out_dir / "ou_parameters_in_sample.csv")
    print(ou_table.describe())

    selected = ou_table[
        (ou_table["theta"] > config.THETA_MIN)
        & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"] >= config.HALFLIFE_MIN)
        & (ou_table["half_life"] <= config.HALFLIFE_MAX)
    ]
    ou_universe = selected.index.tolist()
    full_universe = ou_table.index.tolist()
    print(f"\nOU-selected universe: {len(ou_universe)} / {len(full_universe)} tickers")
    print(ou_universe)

    # --- 2. Out-of-sample %-return backtests (paper-style) ---
    print("\nBacktesting BBfull (full universe) out-of-sample (2018-2024)...")
    results_full = bollinger.backtest_universe(panel, full_universe, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END)
    ret_full, trades_full = bollinger.aggregate_portfolio(results_full)

    print("Backtesting BBOU (OU-selected universe) out-of-sample (2018-2024)...")
    results_ou = bollinger.backtest_universe(panel, ou_universe, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END)
    ret_ou, trades_ou = bollinger.aggregate_portfolio(results_ou)

    bench_ret = benchmark.pct_change().loc[config.OUT_SAMPLE_START:config.OUT_SAMPLE_END].fillna(0.0)
    common_idx = ret_full.index.union(ret_ou.index).union(bench_ret.index)
    ret_full = ret_full.reindex(common_idx, fill_value=0.0)
    ret_ou = ret_ou.reindex(common_idx, fill_value=0.0)
    bench_ret = bench_ret.reindex(common_idx).fillna(0.0)

    m_full = metrics.summarize(ret_full, trades_full)
    m_ou = metrics.summarize(ret_ou, trades_ou)
    m_bench = metrics.summarize(bench_ret)
    summary = pd.DataFrame({"BBfull": m_full, "BBOU": m_ou, bench_label: m_bench}).T
    summary.to_csv(out_dir / "performance_summary.csv")
    print(f"\n=== %-return performance summary (out-of-sample 2018-2024) ===")
    print(summary.round(3).to_string())

    # --- 3. $100k risk-based equity curve ---
    print(f"\nSimulating ${config.INITIAL_EQUITY:,.0f} account (risk_pct={config.RISK_PCT_PER_TRADE:.1%}, "
          f"max_total_risk={config.MAX_TOTAL_RISK_PCT:.1%})...")
    equity_full, dollar_trades_full = portfolio.simulate_portfolio(
        panel, full_universe, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END)
    equity_ou, dollar_trades_ou = portfolio.simulate_portfolio(
        panel, ou_universe, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END)

    bench_window = benchmark.loc[config.OUT_SAMPLE_START:config.OUT_SAMPLE_END]
    equity_bench = config.INITIAL_EQUITY * (bench_window / bench_window.iloc[0])

    common_idx2 = equity_full.index.union(equity_ou.index).union(equity_bench.index)
    equity_full = equity_full.reindex(common_idx2).ffill().fillna(config.INITIAL_EQUITY)
    equity_ou = equity_ou.reindex(common_idx2).ffill().fillna(config.INITIAL_EQUITY)
    equity_bench = equity_bench.reindex(common_idx2).ffill().fillna(config.INITIAL_EQUITY)

    equity_curve_df = pd.DataFrame({
        "BBfull": equity_full, "BBOU": equity_ou, bench_label: equity_bench,
    })
    equity_curve_df.to_csv(out_dir / "equity_curve_100k.csv")

    dollar_summary = pd.DataFrame({
        "BBfull": metrics.summarize(equity_full.pct_change().fillna(0.0), dollar_trades_full),
        "BBOU": metrics.summarize(equity_ou.pct_change().fillna(0.0), dollar_trades_ou),
        bench_label: metrics.summarize(equity_bench.pct_change().fillna(0.0)),
    }).T
    dollar_summary["final_equity"] = [equity_full.iloc[-1], equity_ou.iloc[-1], equity_bench.iloc[-1]]
    dollar_summary.to_csv(out_dir / "performance_summary_100k.csv")
    print(f"\n=== $100k account summary (out-of-sample 2018-2024) ===")
    print(dollar_summary.round(2).to_string())

    pd.DataFrame(dollar_trades_full).to_csv(out_dir / "trades_100k_BBfull.csv", index=False)
    pd.DataFrame(dollar_trades_ou).to_csv(out_dir / "trades_100k_BBOU.csv", index=False)

    # --- 4. Plots ---
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(equity_full.index, equity_full.values, label="BB (full universe)", color="#4C72B0")
    ax.plot(equity_ou.index, equity_ou.values, label="BB + OU filter", color="#C44E52")
    ax.plot(equity_bench.index, equity_bench.values, label=bench_label, color="#DD8452")
    ax.set_title(f"{label}: $100k Equity Curve — BBfull vs BBOU vs {bench_label} "
                 f"({config.OUT_SAMPLE_START[:4]}-{config.OUT_SAMPLE_END[:4]})")
    ax.set_ylabel("Kontostand ($)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "equity_curve_100k.png", dpi=150)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    labels = ["Sharpe", "Sortino", "Calmar"]
    x = np.arange(len(labels))
    width = 0.25
    ax2.bar(x - width, [m_full[k] for k in ["sharpe", "sortino", "calmar"]], width, label="BBfull")
    ax2.bar(x, [m_ou[k] for k in ["sharpe", "sortino", "calmar"]], width, label="BBOU")
    ax2.bar(x + width, [m_bench[k] for k in ["sharpe", "sortino", "calmar"]], width, label=bench_label)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_title(f"{label}: Risk-adjusted performance comparison")
    ax2.legend()
    ax2.grid(alpha=0.3, axis="y")
    fig2.tight_layout()
    fig2.savefig(out_dir / "risk_adjusted_comparison.png", dpi=150)
    plt.close(fig2)

    print(f"\nSaved results to {out_dir}")


if __name__ == "__main__":
    keys = sys.argv[1:] or ["sp500", "nasdaq100"]
    config.RESULTS_DIR.mkdir(exist_ok=True)
    for key in keys:
        run_pipeline(key)
