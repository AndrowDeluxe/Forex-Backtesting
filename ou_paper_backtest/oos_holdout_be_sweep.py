"""BE-trigger sweep on top of the just-adopted final combination (stop_sigma=3.0,
rr_ratio=1.5 fixed TP, risk_pct=0.25%, max_total_risk_pct=5%) -- be_trigger_r was
held fixed at 0.25 (finding 3's value, established at the OLD 1%/15% risk regime)
throughout all of today's SL/TP/risk_pct/cap re-tuning, never itself re-swept at
the new settings. Same genuine 2025+ S&P holdout, same funded-challenge rule checks."""

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

STOP_SIGMA = 3.0
RR_RATIO = 1.5
RISK_PCT = 0.0025
MAX_TOTAL_RISK_PCT = 0.05
BE_TRIGGERS = [0.0, 0.1, 0.25, 0.35, 0.5, 0.75, 1.0]


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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, SL={STOP_SIGMA}, TP=1:{RR_RATIO}, "
          f"risk_pct={RISK_PCT}, cap={MAX_TOTAL_RISK_PCT}\n")

    rows = []
    for be in BE_TRIGGERS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=STOP_SIGMA, rr_ratio=RR_RATIO,
            be_trigger_r=be, allowed_directions=(1,), regime_filter=regime,
            risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
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
            "be_trigger_r": be, **m, "final_equity": eq.iloc[-1],
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "breached_3pct_daily_rule": breached, "days_to_10pct_target": days_to_10pct,
        })
        print(f"  be_trigger_r={be}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
              f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.1f}% "
              f"worst_day={worst_day_pct:.2f}% 3%-Regel_verletzt={breached} "
              f"10%-Ziel_nach={days_to_10pct}_Tagen trades={m['n_trades']} ({time.time()-t0:.1f}s)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_be_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("sharpe", ascending=False).to_string(index=False))
