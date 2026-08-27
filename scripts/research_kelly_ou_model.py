"""Kelly-Formel-Test auf dem OU-Modell (S&P 500, finale gesperrte Config).

Beantwortet: was sagt die Kelly-Formel (f* = p - q/b, angewandt auf R-Vielfache
pro Trade) ueber die Positionsgroesse, verglichen mit dem tatsaechlich
verwendeten risk_pct=1% (gesperrte Config, siehe fertige_strategien.py) bzw.
dem Live-Bot (0.25%/2.5%-Deckel, siehe risk_management.py)?

Zwei Beine, exakt dieselbe gesperrte Logik wie run_final_leg() in
app_pages/fertige_strategien.py (long-only, OU-selektiertes Universum,
3.0-Sigma-SL, kein TP, 0.25R-Breakeven, markt-weiter EMA200-Regimefilter):

1. In-Sample/2018-2024 (aus dem gecachten Panel, kein Download noetig).
2. Echter Out-of-Sample-Holdout 2025-heute (frischer yfinance-Download,
   gleiches Muster wie oos_holdout_riskcap.py) -- weil dieses Projekt
   durchgehend zeigt, dass In-Sample-Befunde sich auf echten Holdouts
   umdrehen koennen (siehe risk_management.py).

R-Vielfaches pro Trade wird approximiert als pnl_dollars / (risk_pct *
equity_at_entry), wobei equity_at_entry aus der taeglichen Equity-Kurve
(eq.asof(entry_date)) genommen wird -- die Positionsgroesse in
simulate_bracket_portfolio() macht ohnehin genau das (shares =
risk_dollars/stop_distance mit risk_dollars = equity*risk_pct), die Annaeherung
weicht nur durch das Abrunden der Shares (np.floor) und ggf. den
max_position_pct-Deckel leicht ab.

WICHTIGE EINSCHRAENKUNG: die klassische Kelly-Formel unterstellt EINE Wette
nach der anderen (sequenziell, unabhaengig). Dieses Portfolio haelt oft viele
Positionen gleichzeitig -- die eigentliche Draw-down-Determinante ist laut
risk_management.py der AGGREGIERTE Deckel (max_total_risk_pct), nicht
risk_pct pro Einzeltrade. Kelly hier liefert daher eine Referenzgroesse fuer
"wie viel Risiko pro EINZELNEM Trade-Slot", kein vollstaendiges
Portfolio-Sizing-Modell.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import portfolio  # noqa: E402

RISK_PCT = 0.01  # gesperrte finale Config (fertige_strategien.py run_final_leg)
HOLDOUT_START = "2025-01-01"
DOWNLOAD_START = "2024-01-01"


def kelly_stats(trades: list[dict], eq: pd.Series, risk_pct: float) -> dict:
    eq = eq.sort_index()
    r_multiples = []
    for tr in trades:
        entry_date = pd.Timestamp(tr["entry_date"])
        idx = eq.index.searchsorted(entry_date, side="right") - 1
        idx = max(idx, 0)
        equity_at_entry = eq.iloc[idx]
        risk_dollars = equity_at_entry * risk_pct
        if risk_dollars <= 0:
            continue
        r_multiples.append(tr["pnl_dollars"] / risk_dollars)

    r = np.array(r_multiples)
    n = len(r)
    wins = r[r > 0]
    losses = r[r <= 0]
    p = len(wins) / n if n else float("nan")
    q = 1 - p
    avg_win_r = wins.mean() if len(wins) else float("nan")
    avg_loss_r = losses.mean() if len(losses) else float("nan")  # negative
    b = avg_win_r / abs(avg_loss_r) if avg_loss_r not in (0, float("nan")) and len(losses) else float("nan")
    kelly_f = p - q / b if b == b and b != 0 else float("nan")  # NaN-safe
    return {
        "n_trades": n,
        "win_rate": p,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "payoff_ratio_b": b,
        "kelly_f": kelly_f,
        "half_kelly_f": kelly_f / 2 if kelly_f == kelly_f else float("nan"),
        "quarter_kelly_f": kelly_f / 4 if kelly_f == kelly_f else float("nan"),
        "used_risk_pct": risk_pct,
    }


def load_ou_tickers(universe_key: str) -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def run_in_sample(universe_key: str = "sp500") -> dict:
    tickers = load_ou_tickers(universe_key)
    panel = pd.read_parquet(config.DATA_CACHE / "_panel.parquet")
    benchmark = pd.read_parquet(config.DATA_CACHE / "IDX_GSPC.parquet").iloc[:, 0]
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).fillna(False)

    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END,
        initial_equity=config.INITIAL_EQUITY, risk_pct=RISK_PCT, max_hold=10,
        stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime,
    )
    stats = kelly_stats(trades, eq, RISK_PCT)
    stats["period"] = f"{config.OUT_SAMPLE_START} .. {config.OUT_SAMPLE_END} (in-sample)"
    stats["final_equity"] = float(eq.iloc[-1])
    return stats


def _download_fresh(tickers: list[str]) -> pd.DataFrame:
    import yfinance as yf

    series = {}
    for i, t in enumerate(tickers):
        df = yf.download(t, start=DOWNLOAD_START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            print(f"  [{i+1}/{len(tickers)}] {t}: no data, skipped")
            continue
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        series[t] = close.dropna()
    print(f"  downloaded {len(series)}/{len(tickers)} tickers")
    return pd.DataFrame(series).sort_index()


def run_holdout(universe_key: str = "sp500") -> dict:
    import yfinance as yf

    tickers = load_ou_tickers(universe_key)
    print(f"[{universe_key}] {len(tickers)} OU-selected tickers, downloading fresh through today...")
    panel = _download_fresh(tickers)

    bench_ticker = config.UNIVERSES[universe_key]["benchmark"]
    bench_df = yf.download(bench_ticker, start=DOWNLOAD_START, auto_adjust=True, progress=False)
    benchmark = bench_df["Close"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark.iloc[:, 0]
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)

    today = panel.index.max().date().isoformat()
    print(f"Holdout window: {HOLDOUT_START} .. {today}")

    eq, trades = portfolio.simulate_bracket_portfolio(
        panel, tickers, HOLDOUT_START, today,
        initial_equity=config.INITIAL_EQUITY, risk_pct=RISK_PCT, max_hold=10,
        stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
        allowed_directions=(1,), regime_filter=regime,
    )
    stats = kelly_stats(trades, eq, RISK_PCT)
    stats["period"] = f"{HOLDOUT_START} .. {today} (echter Out-of-Sample-Holdout)"
    stats["final_equity"] = float(eq.iloc[-1])
    return stats


if __name__ == "__main__":
    t0 = time.time()
    print("=== In-Sample 2018-2024 ===")
    in_sample = run_in_sample()
    for k, v in in_sample.items():
        print(f"  {k}: {v}")

    print("\n=== Out-of-Sample-Holdout 2025-heute ===")
    holdout = run_holdout()
    for k, v in holdout.items():
        print(f"  {k}: {v}")

    out = {"in_sample": in_sample, "holdout": holdout}
    out_path = config.RESULTS_DIR / "sp500" / "kelly_test.json"
    import json
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path}  ({time.time()-t0:.1f}s total)")
