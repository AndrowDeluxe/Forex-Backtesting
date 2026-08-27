"""Verifiziert das OU-Modell auf dem tatsaechlich TTP-handelbaren Universum.

Datenleck-Fund (2026-08-11): das OU-Modell (S&P 500, gesperrte finale Config)
wurde bisher auf ALLEN 147 OU-selektierten Tickern rueckgetestet, obwohl der
Live-Bot (OU-Modell-MT5-Bridge) auf TTPMarkets nur 58 davon ueberhaupt
ausfuehren KANN -- resolve_symbol() dort ueberspringt jedes Signal fuer ein
Symbol, das mt5.symbol_info() nicht liefert (siehe
scripts/build_ttp_tradable_universe.py -> ou_paper_backtest/results/
sp500_ttp_tradable.csv, read-only gegen das TTP-Demo-Terminal geprueft).

Die OU-Parameter (theta/p_value/half_life) sind PRO TICKER unabhaengig
geschaetzt (siehe ou_model.build_ou_summary_table -- kein Cross-Ticker-Bezug),
Filtern auf handelbare Ticker aendert also nicht die OU-Selektion selbst,
nur WELCHE der bereits selektierten Ticker tatsaechlich in den Backtest
eingehen.

Vergleicht dieselbe gesperrte finale Config (long-only, 3.0-Sigma-SL, kein
TP, 0.25R-BE, EMA200-Regimefilter, risk_pct=1%, max_total_risk_pct=15%) auf
zwei Universen, jeweils in-sample (2018-2024) UND auf dem echten
2025-heute-Holdout (Panel wiederverwendet aus dem Kelly-Uncapped-Test von
heute, ou_paper_backtest/data_cache/_holdout_panel_2025_sp500.parquet):

- "unfiltered": alle 147 OU-selektierten Ticker (der bisherige, fehlerhafte Stand)
- "ttp_tradable": nur die 58 davon, die auf TTP tatsaechlich handelbar sind
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402

HOLDOUT_START = "2025-01-01"
HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_sp500.parquet"
HOLDOUT_BENCH_CACHE = OU_DIR / "data_cache" / "_holdout_benchmark_2025_sp500.parquet"


def load_ou_selected_tickers() -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / "sp500" / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def load_ttp_tradable_set() -> set[str]:
    df = pd.read_csv(config.RESULTS_DIR / "sp500_ttp_tradable.csv")
    return set(df[df["ttp_tradable"]]["Symbol"])


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
        "sortino": m["sortino"],
        "calmar": m["calmar"],
        "max_drawdown_pct": m["max_drawdown_pct"],
        "max_concurrent_positions": max_concurrent,
    }


def main() -> dict:
    ou_selected = load_ou_selected_tickers()
    tradable_set = load_ttp_tradable_set()
    ttp_universe = [t for t in ou_selected if t in tradable_set]
    print(f"OU-selektiert: {len(ou_selected)} Ticker")
    print(f"davon TTP-handelbar: {len(ttp_universe)} Ticker")

    universes = {"unfiltered": ou_selected, "ttp_tradable": ttp_universe}

    # --- in-sample (cached panel) ---
    panel_is = pd.read_parquet(config.DATA_CACHE / "_panel.parquet")
    bench_is = pd.read_parquet(config.DATA_CACHE / "IDX_GSPC.parquet").iloc[:, 0]
    regime_is = (bench_is > bench_is.ewm(span=200).mean()).reindex(panel_is.index).fillna(False)

    print("\n=== In-Sample 2018-2024 ===")
    in_sample = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_variant(panel_is, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END, regime_is)
        in_sample[name] = res
        print(f"  {name} ({res['n_tickers']} Ticker): sharpe={res['sharpe']:.2f} "
              f"calmar={res['calmar']:.2f} mdd={res['max_drawdown_pct']:.1f}% "
              f"return={res['total_return_pct']:.0f}% trades={res['n_trades']} "
              f"max_concurrent={res['max_concurrent_positions']} ({time.time()-t0:.1f}s)")

    # --- holdout (cached from heutigem Kelly-Uncapped-Test) ---
    panel_oos = pd.read_parquet(HOLDOUT_CACHE)
    bench_oos = pd.read_parquet(HOLDOUT_BENCH_CACHE).iloc[:, 0]
    regime_oos = (bench_oos > bench_oos.ewm(span=200).mean()).reindex(panel_oos.index).ffill().fillna(False)
    today = panel_oos.index.max().date().isoformat()

    print(f"\n=== Out-of-Sample-Holdout {HOLDOUT_START} .. {today} ===")
    holdout = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_variant(panel_oos, tickers, HOLDOUT_START, today, regime_oos)
        holdout[name] = res
        print(f"  {name} ({res['n_tickers']} Ticker): sharpe={res['sharpe']:.2f} "
              f"calmar={res['calmar']:.2f} mdd={res['max_drawdown_pct']:.1f}% "
              f"return={res['total_return_pct']:.0f}% trades={res['n_trades']} "
              f"max_concurrent={res['max_concurrent_positions']} ({time.time()-t0:.1f}s)")

    return {
        "ou_selected_count": len(ou_selected),
        "ttp_tradable_count": len(ttp_universe),
        "ttp_universe": ttp_universe,
        "in_sample": in_sample,
        "holdout": holdout,
        "holdout_period": f"{HOLDOUT_START} .. {today}",
    }


if __name__ == "__main__":
    t0 = time.time()
    out = main()
    out_path = config.RESULTS_DIR / "sp500" / "ttp_universe_verification.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path} ({time.time()-t0:.1f}s total)")
