"""Re-checks SL/TP/trailing-stop design under the NEW locked risk management
(risk_pct=0.25%, max_total_risk_pct=2.5%, matching the live bot's Konto 2 since
2026-08-07) -- requested because all of findings 2/3 (SL/TP/BE tuning) and the
trailing-stop experiment were originally validated at the OLD risk_pct=1%/
max_total_risk_pct=15% settings. Since the aggregate cap changes how many
positions can be open at once and therefore which trades even get taken, it's
worth re-checking whether "no TP wins" and "trailing loses" still hold at the
new, much tighter sizing -- not assumed to carry over automatically.

One fresh S&P 500 download, four variant groups, all on the genuine 2025+
holdout (never used in any prior sweep):
  A) baseline: stop_sigma=3.0, no TP (today's locked entry/exit, for reference)
  B) smaller/larger SL: stop_sigma in [1.5, 2.0, 2.5, 3.0, 4.0], no TP
  C) fixed TP: stop_sigma=3.0, rr_ratio in [1.0, 1.5, 2.0, 2.5]
  D) trailing stop (std-dev type): trail_mult in [1.5, 2.0, 2.5, 3.0]
All at risk_pct=0.0025, max_total_risk_pct=0.025 throughout.
"""

import sys
import time

import pandas as pd
import yfinance as yf

import config
import metrics
import portfolio

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
RISK_PCT = 0.0025
MAX_TOTAL_RISK_PCT = 0.025
DAILY_LOSS_LIMIT_PCT = -3.0

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
    target_equity = eq.iloc[0] * 1.10
    hit = eq[eq >= target_equity]
    days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None
    row = {
        "variant": label, **params, "final_equity": eq.iloc[-1], **m,
        "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
        "breached_3pct_daily_rule": worst_day_pct < DAILY_LOSS_LIMIT_PCT,
        "days_to_10pct_target": days_to_10pct,
    }
    print(f"  {label:16s} {params}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
          f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.1f}% "
          f"worst_day={worst_day_pct:.2f}% 3%-Regel_verletzt={worst_day_pct < DAILY_LOSS_LIMIT_PCT} "
          f"10%-Ziel_nach={days_to_10pct}_Tagen trades={m['n_trades']} ({time.time()-t0:.1f}s)")
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
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, risk_pct={RISK_PCT}, max_total_risk_pct={MAX_TOTAL_RISK_PCT}\n")

    rows = []

    # A) baseline
    t0 = time.time()
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime, risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
    )
    rows.append(_row("baseline", {"stop_sigma": 3.0, "rr_ratio": None, "trail_mult": None}, eq, trades, t0))

    # B) SL sweep, no TP
    for sigma in STOP_SIGMAS:
        if sigma == 3.0:
            continue  # already have this as baseline
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=sigma, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime, risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
        )
        rows.append(_row("sl_sweep", {"stop_sigma": sigma, "rr_ratio": None, "trail_mult": None}, eq, trades, t0))

    # C) fixed TP sweep at stop_sigma=3.0
    for rr in RR_RATIOS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=rr, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime, risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
        )
        rows.append(_row("fixed_tp", {"stop_sigma": 3.0, "rr_ratio": rr, "trail_mult": None}, eq, trades, t0))

    # D) trailing stop (std-dev)
    for mult in TRAIL_MULTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_trailing_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, trail_type="stddev", trail_mult=mult,
            regime_filter=regime, risk_pct=RISK_PCT, max_total_risk_pct=MAX_TOTAL_RISK_PCT,
        )
        rows.append(_row("trailing", {"stop_sigma": None, "rr_ratio": None, "trail_mult": mult}, eq, trades, t0))

    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    df = run(universe_key)
    out_path = config.RESULTS_DIR / universe_key / "oos_holdout_tpsl_retune.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("sharpe", ascending=False).to_string(index=False))
