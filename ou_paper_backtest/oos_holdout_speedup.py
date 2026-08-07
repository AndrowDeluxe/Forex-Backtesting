"""Follow-up to oos_holdout_tpsl_retune.py: that sweep found stop_sigma=2.0 (no TP)
is the fastest 3%-daily-rule-compliant path to a +10% target on the genuine 2025+
holdout (377 days vs the locked baseline's 579, at risk_pct=0.25%/max_total_risk_pct
=2.5%). Requested (2026-08-07) as a further experiment: can risk_pct/max_total_risk_pct
be pushed up from there to shorten the challenge duration further, while STILL staying
within the 3%-max-single-day-loss rule?

Sweeps risk_pct x max_total_risk_pct on top of the stop_sigma=2.0/no-TP/be=0.25 winner,
one fresh S&P 500 download, same challenge-rule checks as the other challenge-profile
scripts (worst_single_day_pct, breached_3pct_daily_rule, days_to_10pct_target)."""

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
STOP_SIGMA = 2.0  # winner from oos_holdout_tpsl_retune.py

RISK_PCTS = [0.0025, 0.0035, 0.005]
CAPS = [0.025, 0.03, 0.04, 0.05]


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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, stop_sigma={STOP_SIGMA}, kein TP\n")

    rows = []
    for risk_pct in RISK_PCTS:
        for cap in CAPS:
            t0 = time.time()
            eq, trades = portfolio.simulate_bracket_portfolio(
                panel, tickers, HOLDOUT_START, today, stop_sigma=STOP_SIGMA, rr_ratio=None,
                be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
                risk_pct=risk_pct, max_total_risk_pct=cap,
            )
            daily_ret = eq.pct_change().fillna(0.0)
            m = metrics.summarize(daily_ret, trades)
            worst_day_pct = daily_ret.min() * 100
            worst_day_date = daily_ret.idxmin()
            target_equity = eq.iloc[0] * 1.10
            hit = eq[eq >= target_equity]
            days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None
            breached = worst_day_pct < DAILY_LOSS_LIMIT_PCT

            rows.append({
                "risk_pct": risk_pct, "max_total_risk_pct": cap, **m, "final_equity": eq.iloc[-1],
                "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
                "breached_3pct_daily_rule": breached, "days_to_10pct_target": days_to_10pct,
            })
            print(f"  risk_pct={risk_pct:.4f} cap={cap:.3f}: sharpe={m['sharpe']:.2f} "
                  f"calmar={m['calmar']:.2f} mdd={m['max_drawdown_pct']:.1f}% "
                  f"return={m['total_return_pct']:.1f}% worst_day={worst_day_pct:.2f}% "
                  f"3%-Regel_verletzt={breached} 10%-Ziel_nach={days_to_10pct}_Tagen "
                  f"trades={m['n_trades']} ({time.time()-t0:.1f}s)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_speedup.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    compliant = df[~df["breached_3pct_daily_rule"]].dropna(subset=["days_to_10pct_target"])
    print("\n-- Regelkonform, sortiert nach schnellstem 10%-Ziel --")
    print(compliant.sort_values("days_to_10pct_target").to_string(index=False))
