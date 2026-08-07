"""Final two data points for the challenge risk-profile comparison (2026-08-07):
  - 0.5%/2.5%: the EXACT setting currently live on OU-Modell-MT5-Bridge's Konto 2
    (config.py there: risk_pct=0.005, max_total_risk_pct=0.025) -- tested here
    directly for the first time; earlier tests covered 0.25%/2.5% and 0.5%/5%
    (combined book) but never this precise pair alone.
  - 0.5%/4%: requested as one more middle-ground point between 2.5% and 5%.

S&P 500 solo (the diversification test showed DAX dilutes rather than helps),
100k account, same locked entry/exit + genuine 2025+ holdout as every other test
in this series."""

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

PROFILES = [
    ("live_bot_0.5pct_2.5pct", 0.005, 0.025),
    ("middle_0.5pct_4pct", 0.005, 0.04),
]


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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, 100k Startkapital\n")

    rows = []
    for label, risk_pct, cap in PROFILES:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=None,
            be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
            risk_pct=risk_pct, max_total_risk_pct=cap,
        )
        daily_ret = eq.pct_change().fillna(0.0)
        m = metrics.summarize(daily_ret, trades)
        worst_day_pct = daily_ret.min() * 100
        worst_day_date = daily_ret.idxmin()
        target_equity = 100_000 * 1.10
        hit = eq[eq >= target_equity]
        days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None

        rows.append({
            "profile": label, "risk_pct": risk_pct, "max_total_risk_pct": cap,
            **m, "final_equity": eq.iloc[-1],
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "breached_3pct_daily_rule": worst_day_pct < DAILY_LOSS_LIMIT_PCT,
            "days_to_10pct_target": days_to_10pct,
        })
        print(f"  {label}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
              f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.1f}% "
              f"worst_day={worst_day_pct:.2f}% ({worst_day_date.date()}) "
              f"3%-Regel verletzt={worst_day_pct < DAILY_LOSS_LIMIT_PCT} "
              f"trades={m['n_trades']} 10%-Ziel nach={days_to_10pct} Tagen "
              f"({time.time()-t0:.1f}s)")

        eq.loc[HOLDOUT_START:today].to_frame("equity").to_csv(
            config.RESULTS_DIR / universe_key / f"holdout_2025_equity_{label}.csv"
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_final_profiles.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
