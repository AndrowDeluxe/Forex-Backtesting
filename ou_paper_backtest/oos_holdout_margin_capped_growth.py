"""EK-Konto (Konto 3, ~3500 EUR, max leverage 1:30, no other rules) growth
optimization, CORRECTED approach (2026-08-07) after simulate_leveraged_book's pure
margin-maximization sizing blew up catastrophically (30x leverage x ~5-10% stop
distance = 150-300% of margin lost per stop-out, guaranteed ruin). This uses
portfolio.simulate_bracket_portfolio_margin_capped instead: risk_pct still drives
position size (the "Risk Management" being optimized), the leverage ceiling
(equity * 30) is only a backstop on aggregate notional, never the primary sizing
driver.

Sweeps risk_pct from conservative to aggressive on the already-validated exit logic
(stop_sigma=3.0, rr_ratio=1.5 fixed TP, be_trigger_r=0.35 -- the final Konto-2 combo,
see oos_holdout_full_grid.py / oos_holdout_be_sweep.py) to find the profit-maximizing
risk_pct for THIS account's very different objective (raw growth, no drawdown limit)
before the margin ceiling or the strategy's own capacity (how many signals actually
fire) becomes the binding constraint."""

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

RISK_PCTS = [0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20]


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
    print(f"\nHoldout: {HOLDOUT_START} .. {today}, Start={INITIAL_EQUITY} EUR, max_leverage=1:{MAX_LEVERAGE:.0f}, "
          f"SL=3.0, TP=1:1.5, BE=0.35R\n")

    rows = []
    for risk_pct in RISK_PCTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio_margin_capped(
            panel, tickers, HOLDOUT_START, today, initial_equity=INITIAL_EQUITY,
            risk_pct=risk_pct, max_leverage=MAX_LEVERAGE, stop_sigma=3.0, rr_ratio=1.5,
            be_trigger_r=0.35, regime_filter=regime,
        )
        daily_ret = eq.pct_change().fillna(0.0)
        m = metrics.summarize(daily_ret, trades)
        worst_day_pct = daily_ret.min() * 100
        worst_day_date = daily_ret.idxmin()
        blew_up = eq.min() <= 0

        rows.append({
            "risk_pct": risk_pct, **m, "final_equity": eq.iloc[-1], "min_equity": eq.min(),
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "blew_up": blew_up,
        })
        print(f"  risk_pct={risk_pct:.4f}: final=EUR{eq.iloc[-1]:,.0f} return={m['total_return_pct']:.0f}% "
              f"mdd={m['max_drawdown_pct']:.1f}% worst_day={worst_day_pct:.1f}% "
              f"min_equity=EUR{eq.min():,.0f} blew_up={blew_up} trades={m['n_trades']} "
              f"({time.time()-t0:.1f}s)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_margin_capped_growth.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("final_equity", ascending=False).to_string(index=False))
