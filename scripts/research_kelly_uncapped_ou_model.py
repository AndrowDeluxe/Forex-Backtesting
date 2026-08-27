"""Folgetest zu research_kelly_ou_model.py: was passiert, wenn man tatsaechlich mit
Kelly-Groesse pro Trade sizt (statt der gesperrten risk_pct=1%) UND den aggregierten
Risiko-Deckel (max_total_risk_pct) faktisch abschaltet -- die Frage, ob die grosse
Kelly-Luecke aus dem ersten Test wirklich an der Portfolio-Konzentration liegt oder ob
volles Kelly pro Einzeltrade, frei "aufgeteilt auf alle Einzelaktien", tatsaechlich
fahrbar waere.

Kelly-Werte werden AUSSCHLIESSLICH aus dem In-Sample-Fenster (2018-2024) genommen (aus
kelly_test.json) und dann unveraendert auf beide Fenster angewendet -- sonst waere die
Parameterwahl fuer den Holdout-Test selbst schon Data-Snooping.

Getestete Varianten (jeweils in-sample UND auf dem echten 2025-heute-Holdout):
- Baseline: risk_pct=1%, Deckel=15% (die gesperrte Config, zum Vergleich)
- Full-Kelly + Deckel behalten: risk_pct=12.67%, Deckel=15% (zeigt: der Deckel allein
  wuerde bei so hohem risk_pct kaum mehr als eine Position gleichzeitig erlauben)
- Full/Half/Quarter-Kelly, Deckel effektiv abgeschaltet (1000%): zeigt, was passiert,
  wenn Kelly-Groesse frei ueber alle gleichzeitig auftretenden Signale skaliert, ohne
  dass der Deckel eingreift.

max_position_pct (Einzelposition-Notional-Deckel, Default 20%) bleibt in allen Varianten
unveraendert -- der Test betrifft nur den AGGREGIERTEN Risiko-Deckel, nicht den
Einzelpositions-Deckel. Die Simulation modelliert KEINEN Margin Call: Equity kann
unrealistisch negativ werden, weil portfolio.py keinen Broker-Stop-Out simuliert -- ein
echtes Konto waere in so einem Szenario laengst zwangsliquidiert."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_sp500.parquet"
HOLDOUT_BENCH_CACHE = OU_DIR / "data_cache" / "_holdout_benchmark_2025_sp500.parquet"

KELLY_JSON = config.RESULTS_DIR / "sp500" / "kelly_test.json"
NO_CAP = 10.0  # 1000% of equity -- never binds, i.e. "Deckel abgeschaltet"


def load_ou_tickers(universe_key: str) -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def _download_fresh(tickers: list[str]) -> pd.DataFrame:
    import yfinance as yf

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


def get_holdout_panel(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    if HOLDOUT_CACHE.exists() and HOLDOUT_BENCH_CACHE.exists():
        print("  using cached holdout panel (from previous run today)")
        panel = pd.read_parquet(HOLDOUT_CACHE)
        benchmark = pd.read_parquet(HOLDOUT_BENCH_CACHE).iloc[:, 0]
        return panel, benchmark

    import yfinance as yf

    print(f"  downloading fresh holdout panel for {len(tickers)} tickers...")
    panel = _download_fresh(tickers)
    bench_ticker = config.UNIVERSES["sp500"]["benchmark"]
    bench_df = yf.download(bench_ticker, start=DOWNLOAD_START, auto_adjust=True, progress=False)
    benchmark = bench_df["Close"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark.iloc[:, 0]
    panel.to_parquet(HOLDOUT_CACHE)
    benchmark.to_frame("close").to_parquet(HOLDOUT_BENCH_CACHE)
    return panel, benchmark


def run_variant(
    panel: pd.DataFrame, tickers: list[str], start: str, end: str, regime: pd.Series,
    risk_pct: float, max_total_risk_pct: float,
) -> dict:
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, start, end,
        initial_equity=config.INITIAL_EQUITY, risk_pct=risk_pct, max_hold=10,
        stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime,
        max_total_risk_pct=max_total_risk_pct,
    )
    m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
    min_equity = float(eq.min())
    max_concurrent = 0
    # reconstruct max concurrently-open-positions count from trades' entry/exit dates
    events = []
    for tr in trades:
        events.append((pd.Timestamp(tr["entry_date"]), 1))
        events.append((pd.Timestamp(tr["exit_date"]), -1))
    events.sort()
    running = 0
    for _, delta in events:
        running += delta
        max_concurrent = max(max_concurrent, running)

    return {
        "risk_pct": risk_pct,
        "max_total_risk_pct": max_total_risk_pct,
        "n_trades": m.get("n_trades", len(trades)),
        "final_equity": float(eq.iloc[-1]),
        "min_equity": min_equity,
        "went_negative": bool(min_equity < 0),
        "total_return_pct": m["total_return_pct"],
        "sharpe": m["sharpe"],
        "calmar": m["calmar"],
        "max_drawdown_pct": m["max_drawdown_pct"],
        "max_concurrent_positions": max_concurrent,
    }


def main() -> dict:
    kelly_data = json.loads(KELLY_JSON.read_text(encoding="utf-8"))
    kelly_f = kelly_data["in_sample"]["kelly_f"]  # 0.1267 -- in-sample only, no look-ahead
    print(f"In-Sample-Kelly f* = {kelly_f*100:.2f}% (Basis fuer alle Varianten)")

    variants = [
        ("baseline_1pct_15cap", 0.01, 0.15),
        ("full_kelly_15cap", kelly_f, 0.15),
        ("full_kelly_no_cap", kelly_f, NO_CAP),
        ("half_kelly_no_cap", kelly_f / 2, NO_CAP),
        ("quarter_kelly_no_cap", kelly_f / 4, NO_CAP),
    ]

    tickers = load_ou_tickers("sp500")

    # --- in-sample leg (cached panel, fast) ---
    panel_is = pd.read_parquet(config.DATA_CACHE / "_panel.parquet")
    bench_is = pd.read_parquet(config.DATA_CACHE / "IDX_GSPC.parquet").iloc[:, 0]
    regime_is = (bench_is > bench_is.ewm(span=200).mean()).reindex(panel_is.index).fillna(False)

    print("\n=== In-Sample 2018-2024 ===")
    in_sample_results = {}
    for name, rp, cap in variants:
        t0 = time.time()
        res = run_variant(panel_is, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END, regime_is, rp, cap)
        in_sample_results[name] = res
        print(f"  {name}: sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"max_concurrent={res['max_concurrent_positions']} "
              f"min_equity=${res['min_equity']:,.0f} ({time.time()-t0:.1f}s)")

    # --- holdout leg (fresh/cached download) ---
    print("\n=== Out-of-Sample-Holdout 2025-heute ===")
    panel_oos, bench_oos = get_holdout_panel(tickers)
    regime_oos = (bench_oos > bench_oos.ewm(span=200).mean()).reindex(panel_oos.index).ffill().fillna(False)
    today = panel_oos.index.max().date().isoformat()
    print(f"  Holdout window: {HOLDOUT_START} .. {today}")

    holdout_results = {}
    for name, rp, cap in variants:
        t0 = time.time()
        res = run_variant(panel_oos, tickers, HOLDOUT_START, today, regime_oos, rp, cap)
        holdout_results[name] = res
        print(f"  {name}: sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"max_concurrent={res['max_concurrent_positions']} "
              f"min_equity=${res['min_equity']:,.0f} ({time.time()-t0:.1f}s)")

    return {
        "kelly_f_used": kelly_f,
        "variants": {name: {"risk_pct": rp, "max_total_risk_pct": cap} for name, rp, cap in variants},
        "in_sample": in_sample_results,
        "holdout": holdout_results,
        "holdout_period": f"{HOLDOUT_START} .. {today}",
    }


if __name__ == "__main__":
    t0 = time.time()
    out = main()
    out_path = config.RESULTS_DIR / "sp500" / "kelly_uncapped_test.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path} ({time.time()-t0:.1f}s total)")
