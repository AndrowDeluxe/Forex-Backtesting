"""Full cross-product grid: every entry/exit variant from oos_holdout_tpsl_retune.py
(13: baseline, 4 SL values, 4 fixed-TP ratios, 4 trailing multipliers) x every
risk_pct/max_total_risk_pct combo from oos_holdout_speedup.py (12) = up to 156 runs,
one fresh S&P 500 download. Requested (2026-08-07) because the two sweeps were run
SEQUENTIALLY (exit-logic tuned at one fixed risk setting, then risk tuned at one
fixed exit-logic) -- this checks for a synergy neither sequential sweep could see,
before concluding SL=2.0-sigma/no-TP + 0.35%/3% (or similar) is really the best
reachable combination for shortening a funded-challenge timeline without breaching
its 3%-max-daily-loss rule.

Same genuine 2025+ holdout, same challenge-rule checks throughout."""

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

STOP_SIGMAS = [1.5, 2.0, 2.5, 3.0, 4.0]
RR_RATIOS = [1.0, 1.5, 2.0, 2.5]
TRAIL_MULTS = [1.5, 2.0, 2.5, 3.0]
RISK_PCTS = [0.0025, 0.0035, 0.005]
CAPS = [0.025, 0.03, 0.04, 0.05]


def _exit_variants():
    variants = [("baseline", {"stop_sigma": 3.0, "rr_ratio": None})]
    for sigma in STOP_SIGMAS:
        if sigma == 3.0:
            continue
        variants.append((f"sl_{sigma}", {"stop_sigma": sigma, "rr_ratio": None}))
    for rr in RR_RATIOS:
        variants.append((f"tp_{rr}", {"stop_sigma": 3.0, "rr_ratio": rr}))
    return variants


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


def _evaluate(eq: pd.Series, trades: list[dict]) -> dict:
    daily_ret = eq.pct_change().fillna(0.0)
    m = metrics.summarize(daily_ret, trades)
    worst_day_pct = daily_ret.min() * 100
    worst_day_date = daily_ret.idxmin()
    target_equity = eq.iloc[0] * 1.10
    hit = eq[eq >= target_equity]
    days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None
    return {
        "final_equity": eq.iloc[-1], **m,
        "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
        "breached_3pct_daily_rule": worst_day_pct < DAILY_LOSS_LIMIT_PCT,
        "days_to_10pct_target": days_to_10pct,
    }


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
    exit_variants = _exit_variants()
    n_total = len(exit_variants) * len(RISK_PCTS) * len(CAPS) + len(TRAIL_MULTS) * len(RISK_PCTS) * len(CAPS)
    print(f"\nHoldout window: {HOLDOUT_START} .. {today} -- {n_total} combos total\n")

    rows = []
    i = 0
    for exit_label, exit_params in exit_variants:
        for risk_pct in RISK_PCTS:
            for cap in CAPS:
                i += 1
                t0 = time.time()
                eq, trades = portfolio.simulate_bracket_portfolio(
                    panel, tickers, HOLDOUT_START, today, stop_sigma=exit_params["stop_sigma"],
                    rr_ratio=exit_params["rr_ratio"], be_trigger_r=0.25, allowed_directions=(1,),
                    regime_filter=regime, risk_pct=risk_pct, max_total_risk_pct=cap,
                )
                res = _evaluate(eq, trades)
                rows.append({"exit": exit_label, "risk_pct": risk_pct, "max_total_risk_pct": cap, **res})
                if res["days_to_10pct_target"] is not None and not res["breached_3pct_daily_rule"]:
                    print(f"  [{i}/{n_total}] {exit_label:8s} risk={risk_pct:.4f} cap={cap:.3f}: "
                          f"sharpe={res['sharpe']:.2f} mdd={res['max_drawdown_pct']:.1f}% "
                          f"worst_day={res['worst_single_day_pct']:.2f}% "
                          f"10%-Ziel_nach={res['days_to_10pct_target']}_Tagen ({time.time()-t0:.1f}s)")

    for mult in TRAIL_MULTS:
        for risk_pct in RISK_PCTS:
            for cap in CAPS:
                i += 1
                t0 = time.time()
                eq, trades = portfolio.simulate_trailing_bracket_portfolio(
                    panel, tickers, HOLDOUT_START, today, trail_type="stddev", trail_mult=mult,
                    regime_filter=regime, risk_pct=risk_pct, max_total_risk_pct=cap,
                )
                res = _evaluate(eq, trades)
                rows.append({"exit": f"trail_{mult}", "risk_pct": risk_pct, "max_total_risk_pct": cap, **res})
                if res["days_to_10pct_target"] is not None and not res["breached_3pct_daily_rule"]:
                    print(f"  [{i}/{n_total}] trail_{mult:<4} risk={risk_pct:.4f} cap={cap:.3f}: "
                          f"sharpe={res['sharpe']:.2f} mdd={res['max_drawdown_pct']:.1f}% "
                          f"worst_day={res['worst_single_day_pct']:.2f}% "
                          f"10%-Ziel_nach={res['days_to_10pct_target']}_Tagen ({time.time()-t0:.1f}s)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_full_grid.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    compliant = df[~df["breached_3pct_daily_rule"]].dropna(subset=["days_to_10pct_target"])
    print(f"\n-- {len(compliant)}/{len(df)} regelkonform mit erreichtem 10%-Ziel, Top 15 schnellste --")
    print(compliant.sort_values("days_to_10pct_target").head(15).to_string(index=False))
