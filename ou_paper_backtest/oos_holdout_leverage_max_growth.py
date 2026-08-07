"""EK-Konto (own-capital, no drawdown constraint) growth-maximization sweep,
requested (2026-08-07) for Konto 3 (Tickmill, ~3500 EUR, max leverage 1:30 -- the
only real constraint on such an account, no daily-loss or challenge rule at all).
Unlike the funded-challenge work (oos_holdout_*_profiles.py, oos_holdout_full_grid.py),
this optimizes PURELY for final equity/total return on the genuine 2025+ S&P holdout
-- drawdown is reported for information only, never filtered on.

Sizing: portfolio.simulate_leveraged_book/simulate_leveraged_trailing_book (margin/
leverage-based, equal-split across today's candidate signals, capped by
equity*max_leverage - already-committed notional) -- NOT risk_pct-based like every
other script in this package, since a leverage-only account isn't budgeting for
loss, it's budgeting for margin capacity.

Sweeps the same 13 exit-logic variants as oos_holdout_tpsl_retune.py (baseline,
4 SL values, 4 fixed-TP ratios, 4 trailing multipliers) on top of this sizing,
since which exit logic maximizes raw growth without a drawdown constraint can
differ from what won under the funded-challenge's risk discipline."""

import sys
import time

import pandas as pd
import yfinance as yf

import config
import metrics
import portfolio

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
INITIAL_EQUITY = 3500.0
MAX_LEVERAGE = 30.0

STOP_SIGMAS = [1.5, 2.0, 2.5, 3.0, 4.0]
RR_RATIOS = [1.0, 1.5, 2.0, 2.5]
TRAIL_MULTS = [1.5, 2.0, 2.5, 3.0]


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


def _row(label: str, params: dict, eq: pd.Series, trades: list[dict], t0: float) -> dict:
    daily_ret = eq.pct_change().fillna(0.0)
    m = metrics.summarize(daily_ret, trades)
    worst_day_pct = daily_ret.min() * 100
    worst_day_date = daily_ret.idxmin()
    row = {
        "variant": label, **params, "final_equity": eq.iloc[-1], **m,
        "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
    }
    print(f"  {label:12s} {params}: final=EUR{eq.iloc[-1]:,.0f} return={m['total_return_pct']:.0f}% "
          f"sharpe={m['sharpe']:.2f} mdd={m['max_drawdown_pct']:.1f}% worst_day={worst_day_pct:.1f}% "
          f"trades={m['n_trades']} ({time.time()-t0:.1f}s)")
    return row


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
    print(f"\nHoldout: {HOLDOUT_START} .. {today}, Start={INITIAL_EQUITY} EUR, max_leverage=1:{MAX_LEVERAGE:.0f}\n")

    rows = []

    t0 = time.time()
    eq, trades = portfolio.simulate_leveraged_book(
        panel, tickers, HOLDOUT_START, today, initial_equity=INITIAL_EQUITY,
        max_leverage=MAX_LEVERAGE, regime_filter=regime, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
    )
    rows.append(_row("baseline", {"stop_sigma": 3.0, "rr_ratio": None, "trail_mult": None}, eq, trades, t0))

    for sigma in STOP_SIGMAS:
        if sigma == 3.0:
            continue
        t0 = time.time()
        eq, trades = portfolio.simulate_leveraged_book(
            panel, tickers, HOLDOUT_START, today, initial_equity=INITIAL_EQUITY,
            max_leverage=MAX_LEVERAGE, regime_filter=regime, stop_sigma=sigma, rr_ratio=None, be_trigger_r=0.25,
        )
        rows.append(_row("sl_sweep", {"stop_sigma": sigma, "rr_ratio": None, "trail_mult": None}, eq, trades, t0))

    for rr in RR_RATIOS:
        t0 = time.time()
        eq, trades = portfolio.simulate_leveraged_book(
            panel, tickers, HOLDOUT_START, today, initial_equity=INITIAL_EQUITY,
            max_leverage=MAX_LEVERAGE, regime_filter=regime, stop_sigma=3.0, rr_ratio=rr, be_trigger_r=0.25,
        )
        rows.append(_row("fixed_tp", {"stop_sigma": 3.0, "rr_ratio": rr, "trail_mult": None}, eq, trades, t0))

    for mult in TRAIL_MULTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_leveraged_trailing_book(
            panel, tickers, HOLDOUT_START, today, initial_equity=INITIAL_EQUITY,
            max_leverage=MAX_LEVERAGE, regime_filter=regime, trail_mult=mult,
        )
        rows.append(_row("trailing", {"stop_sigma": None, "rr_ratio": None, "trail_mult": mult}, eq, trades, t0))

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_leverage_max_growth.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("final_equity", ascending=False).to_string(index=False))
