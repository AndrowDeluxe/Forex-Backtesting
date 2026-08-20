"""Final portfolio combination (chat 2026-08-20): equal-weighted blend of
the two fully-validated CTNL Edge building blocks, using their FINAL
configs (post trend-filter/re-entry/exit re-optimization, not the
original ones from the first portfolio attempt earlier this session).

  - Continuation: ema_adx_combo/M15 trend filter, direct M5 entry,
    single-position (re-entry confirmed NOT to help here).
  - Reversal cascade: repeat_sweep M15 entry, ATR-5R target, WITH
    re-entry (max_concurrent=3, $100k/1%-risk account - the validated
    breakthrough from this session).

Equal weight (chat 2026-08-20: "gleichgewichtet"): each strategy's OWN
daily return series (whatever internal capital/risk convention it uses)
gets a 0.5 capital weight in the blend - same "sleeve" methodology as
research_gold_smc_portfolio.py earlier this session, just with the final
configs. Reports every BacktestConfig-level parameter for both legs
explicitly, per the user's request.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_account_reentry, simulate_trades_concurrent,
)
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
RISK_PCT = 0.01
STARTING_EQUITY = 100_000.0
MAX_CONCURRENT = 3

# ============================================================ FINAL CONFIGS
CONT_PIPELINE_KWARGS = dict(
    trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5,
)
CONT_BACKTEST_CFG = BacktestConfig(
    spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12,
)

REV_PIPELINE_KWARGS = dict(
    h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep",
)
REV_BACKTEST_CFG = BacktestConfig(
    # winning IS combo from research_gold_smc_reversal_cascade_concurrent_v2.py's
    # sweep (_reversal_concurrent_v2_sweep.csv) was max_hold_h=96 HOURS, i.e.
    # 96/0.25 = 384 M15 bars - NOT 96 bars (which would be 24h). Corrected
    # 2026-08-20 after re-deriving from the saved sweep CSV; the earlier
    # session summary had mis-transcribed this as max_hold_bars=96.
    spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4,
)


def fmt_daily(daily: pd.Series, n_trades: int | None = None) -> str:
    sh, cg, mdd = annualized_sharpe(daily), cagr(daily), max_drawdown(daily)
    total_ret = (1 + daily).prod() - 1
    extra = f"  n_trades={n_trades}" if n_trades is not None else ""
    return f"Sharpe={sh:.2f}  CAGR={cg:+.1%}  TotalReturn={total_ret:+.1%}  MaxDD={mdd:.1%}{extra}"


def print_config_block():
    print("=" * 78)
    print("BACKTEST PARAMETER - BEIDE BAUSTEINE")
    print("=" * 78)
    print("\n--- CONTINUATION ---")
    print("Pipeline (gold_smc_htf_ltf/continuation.py::run_pipeline):")
    for k, v in CONT_PIPELINE_KWARGS.items():
        print(f"  {k} = {v!r}")
    print("  trend_df = M15")
    print("BacktestConfig:")
    for k, v in CONT_BACKTEST_CFG.__dict__.items():
        print(f"  {k} = {v!r}")
    print("Engine: strategy.backtest.simulate_trades (Einzelposition, kein Re-Entry - bestaetigt nicht hilfreich)")

    print("\n--- REVERSAL-KASKADE ---")
    print("Pipeline (gold_smc_htf_ltf/reversal_cascade.py::run_pipeline):")
    for k, v in REV_PIPELINE_KWARGS.items():
        print(f"  {k} = {v!r}")
    print("BacktestConfig:")
    for k, v in REV_BACKTEST_CFG.__dict__.items():
        note = "  # = 96h" if k == "max_hold_bars" else ""
        print(f"  {k} = {v!r}{note}")
    print(f"Engine: gold_smc_htf_ltf/concurrent_backtest.py (Re-Entry erlaubt)")
    print(f"  starting_equity = ${STARTING_EQUITY:,.0f}")
    print(f"  risk_pct = {RISK_PCT:.1%} des aktuellen Eigenkapitals pro Trade")
    print(f"  max_concurrent = {MAX_CONCURRENT} gleichzeitig offene Positionen")

    print("\n--- GEMEINSAM ---")
    print(f"  Instrument: GOLD (XAUUSD), Dukascopy-Daten")
    print(f"  Zeitraum: {START} bis {END}")
    print(f"  IS/OOS-Split: {SPLIT.date()}")
    print(f"  spread_bps: {SPREAD_BPS} (Round-Trip-Kosten)")
    print(f"  Portfolio-Gewichtung: 50% Continuation / 50% Reversal-Kaskade (je eigene Kapital-\"Sleeve\")")


def main():
    print_config_block()

    print("\n" + "=" * 78)
    print("Lade Daten...")
    print("=" * 78)
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)

    # --- Continuation: single-position ---
    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    cont_oos_sig = cont_sig[cont_sig.index >= SPLIT]
    cont_trades = simulate_trades(cont_oos_sig, CONT_BACKTEST_CFG)
    cont_stats = summarize(cont_trades, cont_oos_sig.index)

    # --- Reversal cascade: re-entry account sim ---
    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)
    rev_oos_sig = rev_sig[rev_sig.index >= SPLIT]
    rev_raw = simulate_trades_concurrent(rev_oos_sig, REV_BACKTEST_CFG)
    rev_sim = simulate_account_reentry(rev_raw, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)

    # --- shared daily calendar for both legs. trades_to_daily_returns keeps
    # whatever tz its index arg carries (tz-aware here, matching exit_time),
    # while equity_curve_to_daily_returns always strips tz internally - so
    # strip tz from the first leg's output to align both on tz-naive dates. ---
    common_index = pd.DatetimeIndex([SPLIT.normalize(), pd.Timestamp(END, tz="America/New_York").normalize()])

    daily_cont = trades_to_daily_returns(cont_trades, common_index)
    daily_cont.index = daily_cont.index.tz_localize(None)
    daily_rev = equity_curve_to_daily_returns(rev_sim["equity_curve"], common_index)
    daily_cont, daily_rev = daily_cont.align(daily_rev, join="outer", fill_value=0.0)

    print("\n" + "=" * 78)
    print("EINZELSTRATEGIEN (OOS, 2025-08 bis 2026-08)")
    print("=" * 78)
    print(f"  Continuation:      n={cont_stats['n_trades']}  {fmt_daily(daily_cont)}")
    print(f"  Reversal-Kaskade:  n={rev_sim['n_taken']} (davon {rev_sim['n_skipped']} wegen max_concurrent uebersprungen)  {fmt_daily(daily_rev)}")

    print("\n" + "=" * 78)
    print("UEBERLAPP- UND KORRELATIONS-DIAGNOSE")
    print("=" * 78)
    both_active = (daily_cont != 0) & (daily_rev != 0)
    print(f"  Tage mit Continuation-Aktivitaet: {(daily_cont != 0).sum()}")
    print(f"  Tage mit Reversal-Aktivitaet:     {(daily_rev != 0).sum()}")
    print(f"  Tage mit BEIDEN aktiv:            {both_active.sum()}")
    opposing = both_active & (((daily_cont > 0) & (daily_rev < 0)) | ((daily_cont < 0) & (daily_rev > 0)))
    print(f"  Tage beide aktiv UND gegensaetzliches Vorzeichen: {opposing.sum()}")
    corr = daily_cont.corr(daily_rev)
    print(f"  Korrelation der Tagesrenditen: {corr:.3f}")

    print("\n" + "=" * 78)
    print("PORTFOLIO - 50/50 GLEICHGEWICHTET")
    print("=" * 78)
    combined = 0.5 * daily_cont + 0.5 * daily_rev
    print(f"  {fmt_daily(combined)}")

    print("\n" + "=" * 78)
    print("VERGLEICH")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    bh_daily = daily_close.pct_change().fillna(0.0)
    bh_daily.iloc[0] -= SPREAD_BPS / 2 / 1e4
    print(f"  Buy & Hold Gold:          {fmt_daily(bh_daily)}")
    print(f"  Continuation solo:        {fmt_daily(daily_cont)}")
    print(f"  Reversal-Kaskade solo:    {fmt_daily(daily_rev)}")
    print(f"  Portfolio (50/50):        {fmt_daily(combined)}")

    port_sharpe, port_cagr, port_total, port_mdd = annualized_sharpe(combined), cagr(combined), (1 + combined).prod() - 1, max_drawdown(combined)
    bh_sharpe, bh_cagr = annualized_sharpe(bh_daily), cagr(bh_daily)
    print(f"\n  Portfolio schlaegt Buy&Hold im Sharpe? {'JA' if port_sharpe > bh_sharpe else 'nein'}")
    print(f"  Portfolio schlaegt Buy&Hold in der Gesamtrendite? {'JA' if port_total > ((1+bh_daily).prod()-1) else 'nein'}")


if __name__ == "__main__":
    main()
