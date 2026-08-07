"""Trailing-stop sweep vs. the locked fixed-CRV bracket baseline (stop_sigma=3.0,
no TP, be_trigger_r=0.25), across all 3 markets' OU-selected universes, out-of-sample
(config.OUT_SAMPLE_START..END) -- requested (2026-08-06) as a "step back" to see
whether letting winners run beats a fixed stop + one-shot breakeven move.

Needs an ATR panel per market for the "atr" trail type -- run
`python atr_data.py <universe_key>` first (writes data_cache/_atr_panel_<key>.parquet).
"""

import time

import pandas as pd

import config
import metrics
import portfolio
import run as run_module

STDDEV_MULTS = [1.5, 2.0, 2.5, 3.0, 4.0]
ATR_MULTS = [2.0, 3.0, 4.0, 5.0]
PCT_TRAILS = [0.05, 0.08, 0.10, 0.15]


def _ou_selected_tickers(universe_key: str) -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def _regime_filter(universe_key: str, panel: pd.DataFrame) -> pd.Series:
    benchmark = run_module.load_benchmark(universe_key)
    return (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).fillna(False)


def _row(label: str, params: dict, eq: pd.Series, trades: list[dict], t0: float) -> dict:
    m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
    row = {
        "variant": label, **params,
        "final_equity": eq.iloc[-1], "total_return_pct": m["total_return_pct"],
        "sharpe": m["sharpe"], "sortino": m["sortino"], "calmar": m["calmar"],
        "max_drawdown_pct": m["max_drawdown_pct"], "n_trades": m["n_trades"],
        "win_rate_pct": m["win_rate_pct"], "avg_days_held": m["avg_days_held"],
    }
    print(f"  {label:14s} {params}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
          f"mdd={m['max_drawdown_pct']:.1f}% trades={m['n_trades']} ({time.time()-t0:.1f}s)")
    return row


def sweep(universe_key: str) -> pd.DataFrame:
    panel = run_module.load_panel(universe_key)
    tickers = _ou_selected_tickers(universe_key)
    regime = _regime_filter(universe_key, panel)
    start, end = config.OUT_SAMPLE_START, config.OUT_SAMPLE_END

    atr_path = config.DATA_CACHE / f"_atr_panel_{universe_key}.parquet"
    atr_panel = pd.read_parquet(atr_path) if atr_path.exists() else None
    if atr_panel is None:
        print(f"  [{universe_key}] no ATR panel found at {atr_path} -- skipping atr trail type "
              f"(run `python atr_data.py {universe_key}` first)")

    rows = []

    t0 = time.time()
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, start, end, stop_sigma=3.0,
        rr_ratio=None, be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
    )
    rows.append(_row("baseline_fixed", {"stop_sigma": 3.0}, eq, trades, t0))

    for mult in STDDEV_MULTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_trailing_bracket_portfolio(
            panel, tickers, start, end, trail_type="stddev", trail_mult=mult, regime_filter=regime,
        )
        rows.append(_row("trail_stddev", {"trail_mult": mult}, eq, trades, t0))

    if atr_panel is not None:
        for mult in ATR_MULTS:
            t0 = time.time()
            eq, trades = portfolio.simulate_trailing_bracket_portfolio(
                panel, tickers, start, end, trail_type="atr", trail_mult=mult,
                atr_panel=atr_panel, regime_filter=regime,
            )
            rows.append(_row("trail_atr", {"trail_mult": mult}, eq, trades, t0))

    for pct in PCT_TRAILS:
        t0 = time.time()
        eq, trades = portfolio.simulate_trailing_bracket_portfolio(
            panel, tickers, start, end, trail_type="pct", trail_pct=pct, regime_filter=regime,
        )
        rows.append(_row("trail_pct", {"trail_pct": pct}, eq, trades, t0))

    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    print(f"=== Trailing-SL sweep: {universe_key} ===")
    df = sweep(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "sweep_trailing.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("sharpe", ascending=False).to_string(index=False))
