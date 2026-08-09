"""Walk-forward validation of the Execution-Overlay entry mode (see
scripts/research_gold_execution_overlay.py's screening result: PF 1.426 ->
1.804, IS/OOS both improved, outlier-robust) - does choosing "overlay" over
"wick" based only on strictly-prior years actually hold up forward, year by
year, the same discipline already applied to the ADX/Trend-Bias/Delay/
ExitTime candidates in this project? Then: apply 0.5% fixed-fractional
risk-based position sizing (ATR-free version - the ASB's own stop_distance
from the range width IS the risk-defining stop here, no separate ATR stop
needed like the Gold-Bitcoin engine) to the walk-forward-selected trade
sequence and report the compounded-equity metrics that actually matter for
funded-account-style risk management (CAGR, Sharpe, MaxDD, Calmar).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.execution_overlay import simulate_asian_breakout_overlay
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
)
from asian_range_breakout.walkforward import run_execution_mode_walk_forward
from combined_strategy.data import fetch_timeframe
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import max_drawdown, summarize, trade_stats

TTP_MAX_DAILY_DD = 0.03
TTP_MAX_TOTAL_DD = 0.07

START, END = "2016-01-01", "2026-07-29"
RISK_PCT = 0.005
START_TEST_YEAR, END_TEST_YEAR = 2019, 2026


def production_stack(trades, daily_close_gold, daily_close_silver):
    t = apply_adx_filter(trades, adx_min=15)
    t = apply_trend_bias_filter(t, daily_close_gold, sma_window=200)
    t = apply_entry_delay_filter(t, max_delay_bars=3)
    t = apply_silver_alignment_filter(t, daily_close_silver, window=5)
    return t.sort_values("entry_time").reset_index(drop=True)


def apply_risk_sizing(trades: pd.DataFrame, risk_pct: float, allow_leverage: bool = False) -> pd.DataFrame:
    t = trades.copy()
    stop_distance_pct = t["stop_distance"] / t["entry_price"]
    t["stop_distance_pct"] = stop_distance_pct
    raw_fraction = risk_pct / stop_distance_pct
    t["notional_fraction"] = raw_fraction if allow_leverage else raw_fraction.clip(upper=1.0)
    t["return_pct_raw"] = t["return_pct"]
    t["return_pct"] = t["notional_fraction"] * t["return_pct_raw"]
    return t


def fmt_summary(s: dict) -> str:
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"CAGR={s['cagr']:+.2%}  Sharpe={s['sharpe']:.2f}  MaxDD={s['max_drawdown']:.2%}  Calmar={s['calmar']:.2f}"
    )


def main():
    print(f"Fetching GOLD/SILVER M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    print("Simulating wick-mode and overlay-mode trades + full filter stack...")
    trades_wick_raw = simulate_asian_breakout(df)
    trades_overlay_raw = simulate_asian_breakout_overlay(df)
    prod_wick = production_stack(trades_wick_raw, daily_close_gold, daily_close_silver)
    prod_overlay = production_stack(trades_overlay_raw, daily_close_gold, daily_close_silver)

    print("\n" + "=" * 100)
    print(f"1. EXECUTION-MODE WALK-FORWARD (Test-Jahre {START_TEST_YEAR}-{END_TEST_YEAR}, default=wick)")
    print("=" * 100)
    summary, wf_trades = run_execution_mode_walk_forward(
        {"wick": prod_wick, "overlay": prod_overlay}, default_mode="wick",
        start_test_year=START_TEST_YEAR, end_test_year=END_TEST_YEAR, min_train_trades=30,
    )
    print(summary.to_string(index=False))
    n_years_overlay = (summary["chosen_mode"] == "overlay").sum()
    print(f"\nOverlay wurde in {n_years_overlay}/{len(summary)} Testjahren gewaehlt (train-only, kein Lookahead).")

    print("\n" + "=" * 100)
    print(f"2. RISIKO-BASIERTES SIZING ({RISK_PCT:.1%} pro Trade) -- Walk-Forward-Sequenz vs. statische Baselines")
    print("=" * 100)
    wf_risk = apply_risk_sizing(wf_trades, RISK_PCT)
    wick_only_wf = prod_wick[(prod_wick["entry_time"].dt.year >= START_TEST_YEAR) & (prod_wick["entry_time"].dt.year <= END_TEST_YEAR)]
    wick_only_risk = apply_risk_sizing(wick_only_wf, RISK_PCT)
    overlay_only_wf = prod_overlay[(prod_overlay["entry_time"].dt.year >= START_TEST_YEAR) & (prod_overlay["entry_time"].dt.year <= END_TEST_YEAR)]
    overlay_only_risk = apply_risk_sizing(overlay_only_wf, RISK_PCT)

    for label, trades_risk in [
        ("Walk-Forward (wick/overlay je Jahr gewaehlt)", wf_risk),
        ("Nur Wick (heutige Produktion, statisch)", wick_only_risk),
        ("Nur Overlay (statisch, kein Walk-Forward)", overlay_only_risk),
    ]:
        s = summarize(trades_risk, df.index)
        avg_size = trades_risk["notional_fraction"].mean()
        pct_capped = (trades_risk["notional_fraction"] >= 1.0).mean()
        print(f"  {label}")
        print(f"    {fmt_summary(s)}  avg.Positionsgroesse={avg_size:.1%}  Anteil am 100%-Deckel={pct_capped:.1%}")

    avg_stop_pct = wf_risk["stop_distance_pct"].mean()
    print(f"\n  -> Durchschnittliche Stop-Distanz der ASB selbst: {avg_stop_pct:.2%} des Einstiegspreises.")
    print(
        f"     Bei {RISK_PCT:.1%} Ziel-Risiko waere die 'natuerliche' Positionsgroesse "
        f"{RISK_PCT/avg_stop_pct:.0%} -- der 100%-Deckel (kein Hebel) greift also fast immer, "
        "das reale Risiko je Trade liegt damit naeher an der Stop-Distanz selbst als am 0.5%-Ziel."
    )

    print("\n" + "=" * 100)
    print(f"2b. GLEICHE SEQUENZ MIT HEBEL ERLAUBT (echtes {RISK_PCT:.1%}-Fixed-Fractional-Sizing, kein 100%-Deckel)")
    print("=" * 100)
    wf_risk_lev = apply_risk_sizing(wf_trades, RISK_PCT, allow_leverage=True)
    s_lev = summarize(wf_risk_lev, df.index)
    print(f"  {fmt_summary(s_lev)}  avg.Positionsgroesse={wf_risk_lev['notional_fraction'].mean():.1%} "
          f"(max={wf_risk_lev['notional_fraction'].max():.1%})")
    print(
        "  Setzt voraus, dass der Broker/das Konto genug Hebel auf Gold zulaesst (bei typischen "
        "CFD-Kontenspezifikationen ueblich, z.B. 1:20+) -- unbedingt gegen die tatsaechlichen "
        "Margin-Regeln des jeweiligen Kontos pruefen, bevor das eingesetzt wird."
    )

    print("\n" + "=" * 100)
    print(f"2c. TTP-COMPLIANCE-CHECK -- {RISK_PCT:.1%} Risiko/Trade auf 100k-Fremdkapitalkonto, MIT Hebel")
    print(f"    (Limits: {TTP_MAX_DAILY_DD:.0%} max. Tages-DD / {TTP_MAX_TOTAL_DD:.0%} max. Gesamt-DD)")
    print("=" * 100)
    daily_ret_lev = trades_to_daily_returns(wf_risk_lev, df.index)
    worst_day = daily_ret_lev.min()
    total_dd = max_drawdown(daily_ret_lev)
    n_breach_daily = (daily_ret_lev < -TTP_MAX_DAILY_DD).sum()
    daily_ok = worst_day > -TTP_MAX_DAILY_DD
    total_ok = total_dd > -TTP_MAX_TOTAL_DD
    print(f"  Schlechtester Einzeltag: {worst_day:.2%}  [{'OK' if daily_ok else 'BRUCH'} vs. -{TTP_MAX_DAILY_DD:.0%}]")
    print(f"  Max. Gesamt-Drawdown:    {total_dd:.2%}  [{'OK' if total_ok else 'BRUCH'} vs. -{TTP_MAX_TOTAL_DD:.0%}]")
    print(f"  Tage mit Bruch der Tages-Grenze: {n_breach_daily}")
    print(f"  TTP-konform (beide Grenzen): {'JA' if (daily_ok and total_ok) else 'NEIN'}")

    print("\n" + "=" * 100)
    print("2d. RISIKO-SWEEP -- wie viel Spielraum ist bis zu den TTP-Limits noch da?")
    print("=" * 100)
    for rp in [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04]:
        sim = apply_risk_sizing(wf_trades, rp, allow_leverage=True)
        s = summarize(sim, df.index)
        daily = trades_to_daily_returns(sim, df.index)
        worst = daily.min()
        tot_dd = max_drawdown(daily)
        ok = (worst > -TTP_MAX_DAILY_DD) and (tot_dd > -TTP_MAX_TOTAL_DD)
        print(
            f"  {rp:.1%} Risiko: CAGR={s['cagr']:+.2%}  Sharpe={s['sharpe']:.2f}  "
            f"GesamtDD={tot_dd:.2%}  SchlechtesterTag={worst:.2%}  avg.Hebel={sim['notional_fraction'].mean():.0%}  "
            f"[{'OK' if ok else 'BRUCH'}]"
        )

    print("\n" + "=" * 100)
    print(f"3. AUSREISSER-CHECK -- Walk-Forward + {RISK_PCT:.1%} Risiko (bester Trade entfernt)")
    print("=" * 100)
    sorted_ret = wf_risk["return_pct_raw"].sort_values(ascending=False)
    without_best = wf_risk.drop(index=sorted_ret.index[0])
    s_full = trade_stats(wf_risk)
    s_wo = trade_stats(without_best)
    print(f"  Voller PF (Trade-Ebene):         {s_full['profit_factor']:.3f}")
    print(f"  Ohne besten Trade PF:            {s_wo['profit_factor']:.3f}")

    print(
        "\nHinweis: 'stop_distance' der ASB (Range-Breite x stop_frac) definiert hier direkt die "
        "Risikodistanz fuer 0.5%-Sizing - kein separater ATR-Stop noetig wie beim Gold-Bitcoin-Modell, "
        "die ASB hat schon einen echten Preis-Stop im Regelwerk. avg.Positionsgroesse zeigt, wie viel "
        "vom Konto im Schnitt je offenem Trade eingesetzt wird (gedeckelt auf 100%, kein Hebel)."
    )


if __name__ == "__main__":
    main()
