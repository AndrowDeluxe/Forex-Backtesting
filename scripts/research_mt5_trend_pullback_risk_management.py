"""Risk-parameter calibration for two Fremdkapital (funded/prop) challenge
profiles and one Eigenkapital (personal capital) profile, using the daily
mark-to-market engine in mt5_trend_pullback/daily_risk_engine.py ("die
bisherige Logik" from gold_bitcoin_dual_momentum/risk_engine.py, extended to
this strategy's multi-market/multi-concurrent-position portfolio).

Deliberately run on the FULL 2016-2026 history (not just the favourable
2023-2026 regime) - a real funded account or personal account has to survive
whatever regime happens next, and this strategy was flat-to-losing in every
market 2016-2022 (scripts/research_mt5_trend_pullback.py). Calibrating risk
limits only against the good years would be a dangerous form of the same
overfitting mistake found throughout this research series.

Portfolio: the current standard (Gold, Silver filtered by Gold-alignment,
CHFJPY, USDJPY, USDCAD as a trial addition - Platinum dropped), bot default
parameters (no ADX filter).

Profiles:
  FK1 ("TTP-style"): max daily DD 3%, max total DD 7%
  FK2 ("IQ Markets"): max daily DD 1%, max total DD 8%
  EK  (personal):     no daily limit,  max total DD 20%

For each profile: sweep risk_pct at max_concurrent=3 (the bot's own real
constraint) to find the largest compliant risk_pct, a max_concurrent
sensitivity check (2 vs 3), and a uniform-vs-Sharpe-weighted per-market risk
split check at the chosen setting.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.daily_risk_engine import sweep_risk_pct
from mt5_trend_pullback.filters import alignment_filter
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
STARTING_EQUITY = 100_000.0

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
    ("USDCAD", "H4", "USDCAD", 1.5),
]

RISK_PCT_CANDIDATES = [0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.03]

PROFILES = {
    "FK1 (TTP-Stil: 3% daily / 7% total)": {"daily": 0.03, "total": 0.07},
    "FK2 (IQ Markets: 1% daily / 8% total)": {"daily": 0.01, "total": 0.08},
    "EK (Eigenkapital: kein daily / 20% total)": {"daily": None, "total": 0.20},
}


def main():
    trades_by_market = {}
    daily_low_by_market = {}
    full_sharpe = {}

    gold_d1 = fetch_timeframe("GOLD", "D1", DATA_START, DATA_END)["Close"]
    if gold_d1.index.tz is not None:
        gold_d1.index = gold_d1.index.tz_localize(None)

    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0)
        trades = simulate_trades(signaled, cfg)
        if label == "XAGUSD":
            trades = alignment_filter(trades, gold_d1)
        trades_by_market[label] = trades
        full_sharpe[label] = summarize(trades, signaled.index)["sharpe"]

        daily_low = df["low"].resample("1D").min().dropna()
        daily_low_by_market[label] = daily_low

    print("Full-history (2016-2026) per-market Sharpe (bot default, Silver aligned):")
    for label, sh in full_sharpe.items():
        print(f"  {label:<8} Sharpe={sh:.2f}  n={len(trades_by_market[label])}")

    print("\n" + "=" * 100)
    print("1. RISK_PCT SWEEP per profile, max_concurrent=3, uniform risk split, FULL 2016-2026 history")
    print("=" * 100)
    chosen = {}
    for profile_name, limits in PROFILES.items():
        print(f"\n{profile_name}:")
        sweep = sweep_risk_pct(
            trades_by_market, daily_low_by_market, RISK_PCT_CANDIDATES,
            max_daily_dd_limit=limits["daily"], max_total_dd_limit=limits["total"],
            starting_equity=STARTING_EQUITY, max_concurrent=3,
        )
        for _, row in sweep.iterrows():
            flag = "OK" if row["compliant"] else "VERLETZT"
            print(f"  risk_pct={row['risk_pct']:.4f}  max_daily_dd={row['max_daily_dd']:+.2%}  "
                  f"max_total_dd={row['max_total_dd']:+.2%}  final=${row['final_equity']:,.0f}  "
                  f"return={row['total_return']:+.1%}  n={row['n_trades']:.0f}  [{flag}]")
        compliant = sweep[sweep["compliant"]]
        if compliant.empty:
            print("  -> KEIN Kandidat erfuellt beide Limits, auch nicht der kleinste getestete risk_pct.")
            chosen[profile_name] = None
            continue
        best = compliant.loc[compliant["risk_pct"].idxmax()]
        print(f"  -> Gewaehlt (groesster konformer risk_pct): {best['risk_pct']:.4f} "
              f"({best['risk_pct']*100:.2f}%/Trade), final=${best['final_equity']:,.0f} ({best['total_return']:+.1%})")
        chosen[profile_name] = best

    print("\n" + "=" * 100)
    print("2. MAX_CONCURRENT SENSITIVITY (2 vs 3), at each profile's chosen risk_pct")
    print("=" * 100)
    for profile_name, limits in PROFILES.items():
        best = chosen[profile_name]
        if best is None:
            continue
        print(f"\n{profile_name} (risk_pct={best['risk_pct']:.4f}):")
        for mc in [2, 3, 4]:
            sweep = sweep_risk_pct(
                trades_by_market, daily_low_by_market, [best["risk_pct"]],
                max_daily_dd_limit=limits["daily"], max_total_dd_limit=limits["total"],
                starting_equity=STARTING_EQUITY, max_concurrent=mc,
            )
            row = sweep.iloc[0]
            flag = "OK" if row["compliant"] else "VERLETZT"
            print(f"  max_concurrent={mc}  max_daily_dd={row['max_daily_dd']:+.2%}  "
                  f"max_total_dd={row['max_total_dd']:+.2%}  final=${row['final_equity']:,.0f}  "
                  f"return={row['total_return']:+.1%}  [{flag}]")

    print("\n" + "=" * 100)
    print("3. UNIFORM vs. SHARPE-GEWICHTETER RISK-SPLIT, an jedem Profil's gewaehltem risk_pct, max_concurrent=3")
    print("=" * 100)
    avg_sharpe = sum(full_sharpe.values()) / len(full_sharpe)
    weights = {label: max(sh, 0.05) / avg_sharpe for label, sh in full_sharpe.items()}  # floor to avoid zero/negative weight
    print(f"  Sharpe-basierte Gewichte (normiert auf Mittel=1.0): {', '.join(f'{k}={v:.2f}' for k, v in weights.items())}")
    for profile_name, limits in PROFILES.items():
        best = chosen[profile_name]
        if best is None:
            continue
        print(f"\n{profile_name} (risk_pct={best['risk_pct']:.4f}):")
        for label_split, w in [("uniform", None), ("Sharpe-gewichtet", weights)]:
            sweep = sweep_risk_pct(
                trades_by_market, daily_low_by_market, [best["risk_pct"]],
                max_daily_dd_limit=limits["daily"], max_total_dd_limit=limits["total"],
                starting_equity=STARTING_EQUITY, max_concurrent=3, risk_weight_by_market=w,
            )
            row = sweep.iloc[0]
            flag = "OK" if row["compliant"] else "VERLETZT"
            print(f"  {label_split:<18} max_daily_dd={row['max_daily_dd']:+.2%}  "
                  f"max_total_dd={row['max_total_dd']:+.2%}  final=${row['final_equity']:,.0f}  "
                  f"return={row['total_return']:+.1%}  [{flag}]")


if __name__ == "__main__":
    main()
