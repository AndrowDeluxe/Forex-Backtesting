"""Wie research_ou_model_ttp_universe.py, aber fuer Nasdaq-100 statt S&P 500.

Befund vorab (siehe build_ttp_tradable_universe.py): von 103 Nasdaq-100-Tickern
sind 64 auf TTP handelbar; von den 16 OU-selektierten Nasdaq-100-Tickern nur 8.
Kleines Sample -- Ergebnis ist eher eine Groessenordnung als ein belastbarer
Backtest, aber zeigt dieselbe Datenleck-Frage wie beim S&P 500.

DAX wird hier bewusst NICHT getestet: 0 von 40 DAX-Tickern sind auf TTP
1:1-handelbar (siehe dax_ttp_tradable.csv) -- der einzige Beinahe-Treffer
(MRK.DE -> "MRK") ist eine falsche Namenskollision (Merck KGaA vs. die
comppletely unabhaengige Merck & Co., NYSE), kein echter Fund. Ein Backtest
auf einem leeren Universum ist nicht sinnvoll durchfuehrbar."""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_nasdaq100.parquet"
HOLDOUT_BENCH_CACHE = OU_DIR / "data_cache" / "_holdout_benchmark_2025_nasdaq100.parquet"


def load_ou_selected_tickers() -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / "nasdaq100" / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def load_ttp_tradable_set() -> set[str]:
    df = pd.read_csv(config.RESULTS_DIR / "nasdaq100_ttp_tradable.csv")
    return set(df[df["ttp_tradable"]]["Symbol"])


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
    return pd.DataFrame(series).sort_index()


def get_holdout_panel(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    if HOLDOUT_CACHE.exists() and HOLDOUT_BENCH_CACHE.exists():
        print("  using cached holdout panel")
        return pd.read_parquet(HOLDOUT_CACHE), pd.read_parquet(HOLDOUT_BENCH_CACHE).iloc[:, 0]
    print(f"  downloading fresh holdout panel for {len(tickers)} tickers...")
    panel = _download_fresh(tickers)
    bench_df = yf.download(config.UNIVERSES["nasdaq100"]["benchmark"], start=DOWNLOAD_START,
                            auto_adjust=True, progress=False)
    benchmark = bench_df["Close"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark.iloc[:, 0]
    panel.to_parquet(HOLDOUT_CACHE)
    benchmark.to_frame("close").to_parquet(HOLDOUT_BENCH_CACHE)
    return panel, benchmark


def run_variant(panel: pd.DataFrame, tickers: list[str], start: str, end: str, regime: pd.Series) -> dict:
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, start, end,
        initial_equity=config.INITIAL_EQUITY, risk_pct=0.01, max_hold=10,
        stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime,
        max_total_risk_pct=0.15,
    )
    m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
    events = []
    for tr in trades:
        events.append((pd.Timestamp(tr["entry_date"]), 1))
        events.append((pd.Timestamp(tr["exit_date"]), -1))
    events.sort()
    running = max_concurrent = 0
    for _, delta in events:
        running += delta
        max_concurrent = max(max_concurrent, running)
    return {
        "n_tickers": len(tickers),
        "n_trades": m.get("n_trades", len(trades)),
        "final_equity": float(eq.iloc[-1]),
        "total_return_pct": m["total_return_pct"],
        "sharpe": m["sharpe"],
        "calmar": m["calmar"],
        "max_drawdown_pct": m["max_drawdown_pct"],
        "max_concurrent_positions": max_concurrent,
    }


def main() -> dict:
    ou_selected = load_ou_selected_tickers()
    tradable_set = load_ttp_tradable_set()
    ttp_universe = [t for t in ou_selected if t in tradable_set]
    print(f"OU-selektiert (nasdaq100): {len(ou_selected)} Ticker, davon TTP-handelbar: {len(ttp_universe)}")

    universes = {"unfiltered": ou_selected, "ttp_tradable": ttp_universe}

    panel_is = pd.read_parquet(config.DATA_CACHE / "_panel_nasdaq100.parquet")
    bench_is = pd.read_parquet(config.DATA_CACHE / "IDX_NDX.parquet").iloc[:, 0]
    regime_is = (bench_is > bench_is.ewm(span=200).mean()).reindex(panel_is.index).fillna(False)

    print("\n=== In-Sample 2018-2024 ===")
    in_sample = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_variant(panel_is, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END, regime_is)
        in_sample[name] = res
        print(f"  {name} ({res['n_tickers']}): sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"trades={res['n_trades']} max_concurrent={res['max_concurrent_positions']} ({time.time()-t0:.1f}s)")

    panel_oos, bench_oos = get_holdout_panel(ou_selected)
    regime_oos = (bench_oos > bench_oos.ewm(span=200).mean()).reindex(panel_oos.index).ffill().fillna(False)
    today = panel_oos.index.max().date().isoformat()

    print(f"\n=== Out-of-Sample-Holdout {HOLDOUT_START} .. {today} ===")
    holdout = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_variant(panel_oos, tickers, HOLDOUT_START, today, regime_oos)
        holdout[name] = res
        print(f"  {name} ({res['n_tickers']}): sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"trades={res['n_trades']} max_concurrent={res['max_concurrent_positions']} ({time.time()-t0:.1f}s)")

    return {
        "ou_selected_count": len(ou_selected), "ttp_tradable_count": len(ttp_universe),
        "ttp_universe": ttp_universe, "in_sample": in_sample, "holdout": holdout,
        "holdout_period": f"{HOLDOUT_START} .. {today}",
    }


if __name__ == "__main__":
    t0 = time.time()
    out = main()
    out_path = config.RESULTS_DIR / "nasdaq100" / "ttp_universe_verification.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path} ({time.time()-t0:.1f}s total)")
