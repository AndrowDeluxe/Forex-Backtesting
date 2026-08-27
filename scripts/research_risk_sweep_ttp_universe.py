"""Risk-Management-Sweep auf dem tatsaechlich TTP-handelbaren S&P-Universum (58
statt 147 Ticker, siehe research_ou_model_ttp_universe.py). Beantwortet die Frage
des Users: braucht ein kleineres Universum ein anderes risk_pct/max_total_risk_pct
als die bisherigen, auf 147 Tickern gefundenen Werte?

Zwei Teile, gleiche Disziplin wie sweep_risk_caps.py / oos_holdout_challenge_profiles.py:

1. Abstrakter Sweep von max_total_risk_pct und risk_pct (unabhaengig, jeweils der
   andere bleibt auf dem gesperrten Default) auf 2018-2024 IN-SAMPLE -- das ist die
   Flaeche, auf der man tunen darf, nicht der Holdout.
2. Verifikation auf dem echten 2025-heute-Holdout (gecachtes Panel von heute) fuer
   die bereits bekannten konkreten Profile aus risk_management.py (Konservativ/
   Mittelweg/Aggressiv, S&P-solo) PLUS die aktuell auf Konto 2 laufende Config
   (TP 1:1.5, risk_pct=0.25%, max_total_risk_pct=5%, be_trigger_r=0.35) -- um zu
   pruefen, ob diese sich mit dem kleineren, tatsaechlich handelbaren Universum
   noch genauso verhaelt.

Die "60/40 S&P+DAX"/"50/50 S&P+DAX"-Profile aus risk_management.py werden hier
NICHT wiederholt -- DAX ist mit 0/40 auf TTP handelbaren Tickern fuer dieses Konto
ohnehin nicht umsetzbar (siehe build_ttp_tradable_universe.py)."""

import json
import time
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

import config  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402

HOLDOUT_START = "2025-01-01"
HOLDOUT_CACHE = OU_DIR / "data_cache" / "_holdout_panel_2025_sp500.parquet"
HOLDOUT_BENCH_CACHE = OU_DIR / "data_cache" / "_holdout_benchmark_2025_sp500.parquet"
DAILY_LOSS_LIMIT_PCT = -3.0

MAX_TOTAL_RISK_PCTS = [0.15, 0.125, 0.10, 0.075, 0.05, 0.025]
RISK_PCTS = [0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015]

# (label, risk_pct, max_total_risk_pct, rr_ratio, be_trigger_r)
HOLDOUT_PROFILES = [
    ("konservativ_0.25pct_2.5pct", 0.0025, 0.025, None, 0.25),
    ("mittelweg_0.5pct_4pct", 0.005, 0.04, None, 0.25),
    ("aggressiv_1pct_10pct", 0.01, 0.10, None, 0.25),
    ("konto2_aktuell_tp1.5_0.25pct_5pct_be0.35", 0.0025, 0.05, 1.5, 0.35),
]


def _ttp_universe() -> list[str]:
    ou_table = pd.read_csv(config.RESULTS_DIR / "sp500" / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    tradable = pd.read_csv(config.RESULTS_DIR / "sp500_ttp_tradable.csv")
    tradable_set = set(tradable[tradable["ttp_tradable"]]["Symbol"])
    return [t for t in sel.index.tolist() if t in tradable_set]


def _row(label: str, params: dict, eq: pd.Series, trades: list[dict], t0: float) -> dict:
    m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
    row = {
        "variant": label, **params,
        "final_equity": eq.iloc[-1], "total_return_pct": m["total_return_pct"],
        "sharpe": m["sharpe"], "sortino": m["sortino"], "calmar": m["calmar"],
        "max_drawdown_pct": m["max_drawdown_pct"], "n_trades": m["n_trades"],
        "win_rate_pct": m["win_rate_pct"],
    }
    print(f"  {label:35s} {params}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
          f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.0f}% "
          f"trades={m['n_trades']} ({time.time()-t0:.1f}s)")
    return row


def in_sample_sweep(tickers: list[str]) -> pd.DataFrame:
    panel = pd.read_parquet(config.DATA_CACHE / "_panel.parquet")
    benchmark = pd.read_parquet(config.DATA_CACHE / "IDX_GSPC.parquet").iloc[:, 0]
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).fillna(False)
    start, end = config.OUT_SAMPLE_START, config.OUT_SAMPLE_END

    rows = []
    for cap in MAX_TOTAL_RISK_PCTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, start, end, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime,
            risk_pct=config.RISK_PCT_PER_TRADE, max_total_risk_pct=cap,
        )
        rows.append(_row("max_total_risk_pct", {"max_total_risk_pct": cap, "risk_pct": config.RISK_PCT_PER_TRADE}, eq, trades, t0))

    for rp in RISK_PCTS:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, start, end, stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime,
            risk_pct=rp, max_total_risk_pct=config.MAX_TOTAL_RISK_PCT,
        )
        rows.append(_row("risk_pct", {"max_total_risk_pct": config.MAX_TOTAL_RISK_PCT, "risk_pct": rp}, eq, trades, t0))

    return pd.DataFrame(rows)


def holdout_profiles(tickers: list[str]) -> pd.DataFrame:
    panel = pd.read_parquet(HOLDOUT_CACHE)
    benchmark = pd.read_parquet(HOLDOUT_BENCH_CACHE).iloc[:, 0]
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)
    today = panel.index.max().date().isoformat()
    print(f"\nHoldout window: {HOLDOUT_START} .. {today}, 100k Startkapital, {len(tickers)} Ticker\n")

    rows = []
    for label, risk_pct, cap, rr_ratio, be in HOLDOUT_PROFILES:
        t0 = time.time()
        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, tickers, HOLDOUT_START, today, stop_sigma=3.0, rr_ratio=rr_ratio,
            be_trigger_r=be, allowed_directions=(1,), regime_filter=regime,
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
            "rr_ratio": rr_ratio, "be_trigger_r": be,
            **m, "final_equity": eq.iloc[-1],
            "worst_single_day_pct": worst_day_pct, "worst_day_date": str(worst_day_date.date()),
            "breached_3pct_daily_rule": bool(worst_day_pct < DAILY_LOSS_LIMIT_PCT),
            "days_to_10pct_target": days_to_10pct,
        })
        print(f"  {label}: sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
              f"mdd={m['max_drawdown_pct']:.1f}% return={m['total_return_pct']:.1f}% "
              f"worst_day={worst_day_pct:.2f}% 3%-Regel verletzt={worst_day_pct < DAILY_LOSS_LIMIT_PCT} "
              f"trades={m['n_trades']} 10%-Ziel nach={days_to_10pct} Tagen ({time.time()-t0:.1f}s)")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    tickers = _ttp_universe()
    print(f"TTP-handelbares OU-Universum (S&P): {len(tickers)} Ticker\n")

    print("=== 1. In-Sample-Sweep 2018-2024 ===")
    sweep_df = in_sample_sweep(tickers)
    sweep_path = config.RESULTS_DIR / "sp500" / "sweep_risk_caps_ttp_universe.csv"
    sweep_df.to_csv(sweep_path, index=False)
    print(f"Saved {sweep_path}")

    print("\n=== 2. Holdout-Profile-Verifikation ===")
    profiles_df = holdout_profiles(tickers)
    profiles_path = config.RESULTS_DIR / "sp500" / "oos_holdout_challenge_profiles_ttp_universe.csv"
    profiles_df.to_csv(profiles_path, index=False)
    print(f"Saved {profiles_path}")

    out = {"ttp_universe_size": len(tickers), "sweep": sweep_df.to_dict(orient="records"),
           "holdout_profiles": profiles_df.to_dict(orient="records")}
    (config.RESULTS_DIR / "sp500" / "risk_sweep_ttp_universe.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
