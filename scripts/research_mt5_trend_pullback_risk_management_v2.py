"""Follow-up to scripts/research_mt5_trend_pullback_risk_management.py:

  1. Re-runs the FK1/FK2/EK position-count-cap risk table on the 2023-2026
     window only (not the full 2016-2026 history) - the user's request, for
     a "how would this look calibrated on the current regime" comparison
     point (still, deliberately, NOT the basis for a live risk decision -
     see part 1's caveat).
  2. Finds the largest compliant SCALE of the Sharpe-weighted risk split for
     FK2/EK (the uniform-scale version broke compliance in the prior script -
     scaling the same weight ratios down until compliant again).
  3. Sweeps a breakeven trigger (bot default TP/SL, full 2016-2026 history,
     STANDARD 5-market portfolio) to find a sensible be_trigger_r purely on
     trade-level Sharpe/PF, independent of any portfolio mechanism.
  4. Runs the OU-Modell-style aggregate-open-risk-cap engine (mt5_trend_
     pullback/open_risk_engine.py - "die bisherige Logik", 0.5% risk/trade,
     2% max total open risk, breakeven-exclusion) at the chosen be_trigger_r,
     on both the full history (stress test) and 2023-2026 (current regime),
     and cross-checks it against the FK1/FK2/EK daily/total-DD limits.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.daily_risk_engine import simulate_open_risk_daily, sweep_risk_pct
from mt5_trend_pullback.filters import alignment_filter
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
REGIME_START = pd.Timestamp("2023-01-01", tz="UTC")
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
BE_TRIGGER_CANDIDATES = [None, 0.25, 0.5, 0.75, 1.0, 1.5]


def build_market_data(be_trigger_r: float | None) -> tuple[dict, dict]:
    trades_by_market, daily_low_by_market = {}, {}
    gold_d1 = fetch_timeframe("GOLD", "D1", DATA_START, DATA_END)["Close"]
    if gold_d1.index.tz is not None:
        gold_d1.index = gold_d1.index.tz_localize(None)
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=2.0, use_vwap_target=False, take_profit_r=2.0, breakeven_trigger_r=be_trigger_r)
        trades = simulate_trades(signaled, cfg)
        if label == "XAGUSD":
            trades = alignment_filter(trades, gold_d1)
        trades_by_market[label] = trades
        daily_low_by_market[label] = df["low"].resample("1D").min().dropna()
    return trades_by_market, daily_low_by_market


def slice_trades(trades_by_market: dict, start) -> dict:
    return {m: t[t["entry_time"] >= start] for m, t in trades_by_market.items()}


def main():
    print("=" * 100)
    print("1. FK1/FK2/EK RISK_PCT SWEEP -- 2023-2026 ONLY (nicht die volle Historie)")
    print("=" * 100)
    print("ACHTUNG: nur Referenzpunkt, keine Basis fuer die Live-Entscheidung -- siehe Text.\n")

    trades_full_nobe, daily_low = build_market_data(be_trigger_r=None)
    trades_2023 = slice_trades(trades_full_nobe, REGIME_START)

    chosen_2023 = {}
    for profile_name, limits in PROFILES.items():
        sweep = sweep_risk_pct(
            trades_2023, daily_low, RISK_PCT_CANDIDATES,
            max_daily_dd_limit=limits["daily"], max_total_dd_limit=limits["total"],
            starting_equity=STARTING_EQUITY, max_concurrent=3,
        )
        compliant = sweep[sweep["compliant"]]
        print(f"{profile_name}:")
        for _, row in sweep.iterrows():
            flag = "OK" if row["compliant"] else "VERLETZT"
            print(f"  risk_pct={row['risk_pct']:.4f}  daily={row['max_daily_dd']:+.2%}  total={row['max_total_dd']:+.2%}  "
                  f"final=${row['final_equity']:,.0f}  return={row['total_return']:+.1%}  [{flag}]")
        if compliant.empty:
            print("  -> kein Kandidat konform.\n")
            chosen_2023[profile_name] = None
            continue
        best = compliant.loc[compliant["risk_pct"].idxmax()]
        chosen_2023[profile_name] = best
        print(f"  -> Gewaehlt: {best['risk_pct']:.4f} ({best['risk_pct']*100:.2f}%/Trade), "
              f"final=${best['final_equity']:,.0f} ({best['total_return']:+.1%})\n")

    print("\n" + "=" * 100)
    print("2. SHARPE-GEWICHTETER SPLIT -- kleinste konforme Skalierung fuer FK2 & EK (volle Historie)")
    print("=" * 100)
    full_sharpe = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        full_sharpe[label] = summarize(trades_full_nobe[label], signaled.index)["sharpe"]
    avg_sharpe = sum(full_sharpe.values()) / len(full_sharpe)
    base_weights = {label: max(sh, 0.05) / avg_sharpe for label, sh in full_sharpe.items()}
    print(f"Basis-Gewichte: {', '.join(f'{k}={v:.2f}' for k, v in base_weights.items())}\n")

    for profile_name in ["FK2 (IQ Markets: 1% daily / 8% total)", "EK (Eigenkapital: kein daily / 20% total)"]:
        limits = PROFILES[profile_name]
        # use the full-history-chosen risk_pct from the prior script's result (hardcoded reference, re-derive via sweep at scale=1 uniform for consistency)
        base_sweep = sweep_risk_pct(trades_full_nobe, daily_low, RISK_PCT_CANDIDATES, limits["daily"], limits["total"], STARTING_EQUITY, 3)
        base_compliant = base_sweep[base_sweep["compliant"]]
        base_risk_pct = base_compliant.loc[base_compliant["risk_pct"].idxmax(), "risk_pct"]
        print(f"{profile_name} (Basis risk_pct={base_risk_pct:.4f} auf voller Historie):")
        for scale in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]:
            weights = {m: w * scale for m, w in base_weights.items()}
            sweep = sweep_risk_pct(trades_full_nobe, daily_low, [base_risk_pct], limits["daily"], limits["total"], STARTING_EQUITY, 3, risk_weight_by_market=weights)
            row = sweep.iloc[0]
            flag = "OK" if row["compliant"] else "VERLETZT"
            print(f"  scale={scale:.1f}  daily={row['max_daily_dd']:+.2%}  total={row['max_total_dd']:+.2%}  "
                  f"final=${row['final_equity']:,.0f}  return={row['total_return']:+.1%}  [{flag}]")
        print()

    print("\n" + "=" * 100)
    print("3. BREAKEVEN-TRIGGER SWEEP -- reiner Strategie-Effekt (Bot-Default TP/SL, volle Historie, gepoolt)")
    print("=" * 100)
    for be in BE_TRIGGER_CANDIDATES:
        tbm, _ = build_market_data(be_trigger_r=be)
        trades_pooled = []
        idx_list = []
        for key, tf, label, spread_bps in MARKETS:
            df = fetch_timeframe(key, tf, DATA_START, DATA_END)
            df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
            signaled = run_pipeline(df)
            idx_list.append(signaled.index)
            trades_pooled.append(tbm[label])
        combined_trades = pd.concat(trades_pooled, ignore_index=True)
        full_index = pd.date_range(min(i.min() for i in idx_list), max(i.max() for i in idx_list), freq="D")
        s = summarize(combined_trades, full_index)
        print(f"  be_trigger={str(be):>5}  n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
              f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}")

    CHOSEN_BE = 0.5  # picked after inspecting the sweep above -- see printed table for the actual comparison
    print(f"\n  -> Gewaehlt fuer Teil 4: be_trigger_r={CHOSEN_BE} (siehe Tabelle oben zur Begruendung)")

    print("\n" + "=" * 100)
    print(f"4. OU-MODELL-STIL OPEN-RISK-ENGINE (0.5% Risiko/Trade, 2% max. offenes Risiko, BE={CHOSEN_BE})")
    print("=" * 100)
    trades_be, daily_low_be = build_market_data(be_trigger_r=CHOSEN_BE)

    for period_name, tbm in [("Volle Historie 2016-2026", trades_be), ("Nur 2023-2026", slice_trades(trades_be, REGIME_START))]:
        res = simulate_open_risk_daily(tbm, daily_low_be, risk_pct=0.005, max_total_risk_pct=0.02, starting_equity=STARTING_EQUITY)
        print(f"\n{period_name}:")
        print(f"  n_trades={res.n_trades_taken}  n_skipped={res.n_trades_skipped}")
        print(f"  final_equity=${res.final_equity:,.0f}  return={res.total_return:+.1%}")
        print(f"  max_daily_dd={res.max_daily_dd_pct:+.2%}  max_total_dd={res.max_total_dd_pct:+.2%}")
        for profile_name, limits in PROFILES.items():
            daily_ok = limits["daily"] is None or abs(res.max_daily_dd_pct) <= limits["daily"]
            total_ok = abs(res.max_total_dd_pct) <= limits["total"]
            flag = "OK" if daily_ok and total_ok else "VERLETZT"
            print(f"    vs. {profile_name}: [{flag}]")


if __name__ == "__main__":
    main()
