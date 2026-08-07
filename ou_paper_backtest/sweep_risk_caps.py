"""How much does capping aggregate/per-trade risk actually buy in lower max drawdown,
on the LOCKED baseline config (stop_sigma=3.0, no TP, be_trigger_r=0.25) -- requested
(2026-08-07) after the trailing-stop experiment failed its OOS check and the baseline
stayed the champion. Sweeps max_total_risk_pct (aggregate cap across concurrent
positions) and risk_pct (per-trade risk) independently, holding the other at its
current locked-config default, on the same 2018-2024 out-of-sample window used
everywhere else in this package (NOT the 2025+ holdout, which is reserved as the
one-shot final overfitting check -- reusing it here for parameter selection would
burn it)."""

import time

import pandas as pd

import config
import metrics
import portfolio
import run as run_module

MAX_TOTAL_RISK_PCTS = [0.15, 0.125, 0.10, 0.075, 0.05]
RISK_PCTS = [0.005, 0.0075, 0.01, 0.0125, 0.015]


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
        "win_rate_pct": m["win_rate_pct"],
    }
    print(f"  {label:22s} {params}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
          f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.0f}% "
          f"trades={m['n_trades']} ({time.time()-t0:.1f}s)")
    return row


def sweep(universe_key: str) -> pd.DataFrame:
    panel = run_module.load_panel(universe_key)
    tickers = _ou_selected_tickers(universe_key)
    regime = _regime_filter(universe_key, panel)
    start, end = config.OUT_SAMPLE_START, config.OUT_SAMPLE_END

    rows = []
    for cap in MAX_TOTAL_RISK_PCTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, start, end, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime, max_total_risk_pct=cap,
        )
        rows.append(_row("max_total_risk_pct", {"max_total_risk_pct": cap, "risk_pct": config.RISK_PCT_PER_TRADE}, eq, trades, t0))

    for rp in RISK_PCTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, start, end, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime, risk_pct=rp,
        )
        rows.append(_row("risk_pct", {"max_total_risk_pct": config.MAX_TOTAL_RISK_PCT, "risk_pct": rp}, eq, trades, t0))

    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    print(f"=== Risk-cap sweep: {universe_key} (baseline locked config, varying risk caps only) ===")
    df = sweep(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "sweep_risk_caps.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
