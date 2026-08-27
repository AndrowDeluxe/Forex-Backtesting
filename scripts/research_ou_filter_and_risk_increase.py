"""Zwei Folgefragen zum TTP-Handelbarkeits-Fix (siehe research_ou_model_ttp_universe.py):

1. Wie performt das TTP-handelbare S&P-Universum OHNE den OU-Selektions-Filter
   (also "BBfull"-Stil, wie run.py es nennt) -- 182 statt 58 Ticker (alle TTP-
   handelbaren Ticker, fuer die unser gecachtes Panel Preishistorie hat, ohne
   die theta/p_value/half_life-Vorauswahl)?
2. Wie sieht eine Risikoerhoehung von risk_pct=0.25% auf 0.5% auf dem JETZT
   korrekten (OU-selektiert UND TTP-handelbaren, 58 Ticker) Universum aus,
   bei unveraendertem Konto-2-Setup (TP 1:1.5, max_total_risk_pct=5%,
   be_trigger_r=0.35)? Zusatz: dieselbe Risikoerhoehung auch auf dem
   OU-Filter-freien 182er-Universum, da die Downloads dafuer ohnehin schon
   gemacht werden.

Alles auf zwei Fenstern: 2018-2024 in-sample (gecachtes Panel) und der echte
2025-heute-Holdout (fuer die zusaetzlichen ~124 Ticker, die noch nicht im
gecachten Holdout-Panel von heute frueher sind, frisch heruntergeladen)."""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402

HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"
DAILY_LOSS_LIMIT_PCT = -3.0

EXISTING_HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_sp500.parquet"
EXISTING_HOLDOUT_BENCH = OU_DIR / "data_cache" / "_holdout_benchmark_2025_sp500.parquet"
FULL_HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_sp500_noOU.parquet"


def _load_ou_selected() -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / "sp500" / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def _load_tradable() -> set[str]:
    df = pd.read_csv(config.RESULTS_DIR / "sp500_ttp_tradable.csv")
    return set(df[df["ttp_tradable"]]["Symbol"])


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


def get_full_holdout_panel(target_tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    if FULL_HOLDOUT_CACHE.exists():
        print("  using cached full holdout panel")
        return pd.read_parquet(FULL_HOLDOUT_CACHE), pd.read_parquet(EXISTING_HOLDOUT_BENCH).iloc[:, 0]

    existing = pd.read_parquet(EXISTING_HOLDOUT_CACHE) if EXISTING_HOLDOUT_CACHE.exists() else pd.DataFrame()
    missing = [t for t in target_tickers if t not in existing.columns]
    print(f"  {len(missing)} tickers missing from cached holdout panel, downloading fresh...")
    fresh = _download_fresh(missing) if missing else pd.DataFrame()
    panel = pd.concat([existing, fresh], axis=1) if not fresh.empty else existing
    panel = panel.loc[:, ~panel.columns.duplicated()]
    panel.to_parquet(FULL_HOLDOUT_CACHE)

    benchmark = pd.read_parquet(EXISTING_HOLDOUT_BENCH).iloc[:, 0]
    return panel, benchmark


def run_diagnostic(panel: pd.DataFrame, tickers: list[str], start: str, end: str, regime: pd.Series) -> dict:
    """Gesperrte Forschungs-Baseline (risk_pct=1%, cap=15%, kein TP, be=0.25R) --
    dieselbe wie in research_ou_model_ttp_universe.py, fuer direkte Vergleichbarkeit."""
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, start, end, initial_equity=config.INITIAL_EQUITY,
        risk_pct=0.01, max_hold=10, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime, max_total_risk_pct=0.15,
    )
    m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
    return {"n_tickers": len(tickers), "n_trades": m.get("n_trades", len(trades)),
            "sharpe": m["sharpe"], "calmar": m["calmar"], "max_drawdown_pct": m["max_drawdown_pct"],
            "total_return_pct": m["total_return_pct"], "final_equity": float(eq.iloc[-1])}


def run_konto2_style(panel: pd.DataFrame, tickers: list[str], risk_pct: float, today: str, regime: pd.Series) -> dict:
    """Konto-2-Stil (TP 1:1.5, max_total_risk_pct=5%, be_trigger_r=0.35), nur risk_pct
    variiert -- auf dem echten Holdout, wie die Funded-Challenge-Profile."""
    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today, initial_equity=config.INITIAL_EQUITY,
        risk_pct=risk_pct, max_hold=10, stop_sigma=3.0, rr_ratio=1.5, be_trigger_r=0.35,
        allowed_directions=(1,), regime_filter=regime, max_total_risk_pct=0.05,
    )
    daily_ret = eq.pct_change().fillna(0.0)
    m = metrics.summarize(daily_ret, trades)
    worst_day_pct = daily_ret.min() * 100
    worst_day_date = daily_ret.idxmin()
    target_equity = 100_000 * 1.10
    hit = eq[eq >= target_equity]
    days_to_10pct = (hit.index[0] - eq.index[0]).days if not hit.empty else None
    return {
        "n_tickers": len(tickers), "risk_pct": risk_pct, "n_trades": m.get("n_trades", len(trades)),
        "sharpe": m["sharpe"], "calmar": m["calmar"], "max_drawdown_pct": m["max_drawdown_pct"],
        "total_return_pct": m["total_return_pct"], "final_equity": float(eq.iloc[-1]),
        "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
        "breached_3pct_daily_rule": bool(worst_day_pct < DAILY_LOSS_LIMIT_PCT),
        "days_to_10pct_target": days_to_10pct,
    }


def main() -> dict:
    ou_selected = _load_ou_selected()
    tradable = _load_tradable()

    panel_full_is = pd.read_parquet(config.DATA_CACHE / "_panel.parquet")
    ou_tradable_58 = [t for t in ou_selected if t in tradable]
    no_ou_182 = [t for t in tradable if t in panel_full_is.columns]
    print(f"OU-selektiert & TTP-handelbar: {len(ou_tradable_58)} Ticker")
    print(f"TTP-handelbar, OHNE OU-Filter (Panel-Deckung): {len(no_ou_182)} Ticker")

    universes = {"ou_filter_58": ou_tradable_58, "no_ou_filter_182": no_ou_182}

    bench_is = pd.read_parquet(config.DATA_CACHE / "IDX_GSPC.parquet").iloc[:, 0]
    regime_is = (bench_is > bench_is.ewm(span=200).mean()).reindex(panel_full_is.index).fillna(False)

    print("\n=== 1. OU-Filter-Effekt: Diagnostik-Baseline, In-Sample 2018-2024 ===")
    in_sample = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_diagnostic(panel_full_is, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END, regime_is)
        in_sample[name] = res
        print(f"  {name} ({res['n_tickers']}): sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"trades={res['n_trades']} ({time.time()-t0:.1f}s)")

    print("\n  Lade/downloade Holdout-Panel fuer 182er-Universum...")
    panel_oos, bench_oos = get_full_holdout_panel(no_ou_182)
    regime_oos = (bench_oos > bench_oos.ewm(span=200).mean()).reindex(panel_oos.index).ffill().fillna(False)
    today = panel_oos.index.max().date().isoformat()

    print(f"\n=== 1. OU-Filter-Effekt: Diagnostik-Baseline, Holdout {HOLDOUT_START}..{today} ===")
    holdout = {}
    for name, tickers in universes.items():
        t0 = time.time()
        res = run_diagnostic(panel_oos, tickers, HOLDOUT_START, today, regime_oos)
        holdout[name] = res
        print(f"  {name} ({res['n_tickers']}): sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
              f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.0f}% "
              f"trades={res['n_trades']} ({time.time()-t0:.1f}s)")

    print(f"\n=== 2. Risikoerhoehung auf 0.5% (Konto-2-Stil, Holdout {HOLDOUT_START}..{today}) ===")
    risk_increase = {}
    for uname, tickers in universes.items():
        risk_increase[uname] = {}
        for rp in (0.0025, 0.005):
            t0 = time.time()
            res = run_konto2_style(panel_oos, tickers, rp, today, regime_oos)
            risk_increase[uname][f"risk_pct_{rp}"] = res
            print(f"  {uname} risk_pct={rp*100:.2f}%: sharpe={res['sharpe']:.2f} calmar={res['calmar']:.2f} "
                  f"mdd={res['max_drawdown_pct']:.1f}% return={res['total_return_pct']:.1f}% "
                  f"worst_day={res['worst_single_day_pct']:.2f}% "
                  f"3%-Regel_verletzt={res['breached_3pct_daily_rule']} "
                  f"trades={res['n_trades']} 10%-Ziel={res['days_to_10pct_target']}T ({time.time()-t0:.1f}s)")

    return {
        "in_sample": in_sample, "holdout": holdout, "risk_increase": risk_increase,
        "holdout_period": f"{HOLDOUT_START} .. {today}",
    }


if __name__ == "__main__":
    t0 = time.time()
    out = main()
    out_path = config.RESULTS_DIR / "sp500" / "ou_filter_and_risk_increase.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path} ({time.time()-t0:.1f}s total)")
