"""Middle-ground risk profile (between the earlier conservative 0.25%/2.5% and
aggressive 1%/10% test) PLUS a two-market combined book (S&P 500 + DAX, fixed
capital split), on the genuine 2025+ holdout -- requested (2026-08-07) as a
follow-up to oos_holdout_challenge_profiles.py.

Capital-split combination mirrors app_pages/fertige_strategien.py's run_view():
each market is its own independently-managed book with its own slice of the 100k
starting capital, then equity curves are unioned/ffilled/summed -- NOT a single
shared risk pool across markets (see that file's own note: "'50/50'-Ansichten sind
ein simpler fixer Kapitalsplit zwischen zwei unabhaengig laufenden Buechern").
risk_pct/max_total_risk_pct are applied identically in both books (percentages of
each book's OWN equity), which is why a 50/50 split naturally reproduces the same
effective aggregate-risk percentage on the combined account as running one market
alone at that percentage -- no extra parameter needed for that to hold.

Worst single day % and the 3%-daily-loss-rule check are computed on the COMBINED
curve, since that's what the challenge account actually sees, not on either leg
alone."""

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

MIDDLE_PROFILE = ("middle_0.5pct_5pct", 0.005, 0.05)
SPLITS = [("50/50", 0.50, 0.50), ("60/40", 0.60, 0.40)]


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


def _load_market(universe_key: str) -> tuple[pd.DataFrame, list[str], pd.Series]:
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
    return panel, tickers, regime


def _run_leg(panel, tickers, regime, today, initial_equity, risk_pct, cap):
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=None,
        be_trigger_r=0.25, allowed_directions=(1,), regime_filter=regime,
        initial_equity=initial_equity, risk_pct=risk_pct, max_total_risk_pct=cap,
    )
    return eq, trades


def run() -> pd.DataFrame:
    label, risk_pct, cap = MIDDLE_PROFILE

    panel_sp, tickers_sp, regime_sp = _load_market("sp500")
    panel_dax, tickers_dax, regime_dax = _load_market("dax")
    today = min(panel_sp.index.max(), panel_dax.index.max()).date().isoformat()
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, Profil={label}\n")

    rows = []
    for split_label, w_sp, w_dax in SPLITS:
        t0 = time.time()
        eq_sp, tr_sp = _run_leg(panel_sp, tickers_sp, regime_sp, today, 100_000 * w_sp, risk_pct, cap)
        eq_dax, tr_dax = _run_leg(panel_dax, tickers_dax, regime_dax, today, 100_000 * w_dax, risk_pct, cap)

        common_idx = eq_sp.index.union(eq_dax.index)
        total_eq = (
            eq_sp.reindex(common_idx).ffill().fillna(100_000 * w_sp)
            + eq_dax.reindex(common_idx).ffill().fillna(100_000 * w_dax)
        )
        all_trades = tr_sp + tr_dax

        daily_ret = total_eq.pct_change().fillna(0.0)
        m = metrics.summarize(daily_ret, all_trades)
        worst_day_pct = daily_ret.min() * 100
        worst_day_date = daily_ret.idxmin()
        target_equity = 100_000 * 1.10
        hit = total_eq[total_eq >= target_equity]
        days_to_10pct = (hit.index[0] - total_eq.index[0]).days if not hit.empty else None

        rows.append({
            "split": split_label, "profile": label, "risk_pct": risk_pct, "max_total_risk_pct": cap,
            **m, "final_equity": total_eq.iloc[-1],
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "breached_3pct_daily_rule": worst_day_pct < DAILY_LOSS_LIMIT_PCT,
            "days_to_10pct_target": days_to_10pct,
        })
        print(f"  {split_label} (SP {w_sp:.0%}/DAX {w_dax:.0%}): sharpe={m['sharpe']:.2f} "
              f"calmar={m['calmar']:.2f} mdd={m['max_drawdown_pct']:.1f}% "
              f"return={m['total_return_pct']:.1f}% worst_day={worst_day_pct:.2f}% "
              f"({worst_day_date.date()}) 3%-Regel verletzt={worst_day_pct < DAILY_LOSS_LIMIT_PCT} "
              f"trades={m['n_trades']} 10%-Ziel nach={days_to_10pct} Tagen ({time.time()-t0:.1f}s)")

        total_eq.to_frame("equity").to_csv(
            config.RESULTS_DIR / f"holdout_2025_equity_combined_{split_label.replace('/', '_')}_{label}.csv"
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run()
    out_path = config.RESULTS_DIR / "oos_holdout_combined_profiles.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.to_string(index=False))
