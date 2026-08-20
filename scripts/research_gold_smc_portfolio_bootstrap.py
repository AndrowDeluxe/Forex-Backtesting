"""Professional-backtest step 1/N (chat 2026-08-20): Monte Carlo / block-
bootstrap of the CHOSEN FK (1.00%/0.25%) and EK (2.00%/1.50%) combined
account paths.

Directly addresses the caveat repeated throughout this session: the
MaxDD/TotalReturn numbers reported so far come from ONE realized
historical path (2025-08 to 2026-08). Block-bootstrapping the daily
return series (block size preserves short-run autocorrelation, e.g. a
losing streak clustered in one week) generates many ALTERNATE equally-
likely paths through the SAME underlying trade population, answering:
"how much does the reported MaxDD depend on lucky/unlucky sequencing,
not just on the strategy's real edge?" - directly quantifies the FK
Challenge's real risk-of-ruin (P(MaxDD breaches 6%)), not just the one
number the single historical draw happened to produce.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_combined_account, simulate_trades_concurrent,
)
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
STARTING_EQUITY = 100_000.0
MAX_DD_LIMIT = 0.06
N_SIM = 5000
BLOCK_DAYS = 10
RNG_SEED = 42

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)

MAX_CONCURRENT = {"continuation": None, "reversal": 3}

SCENARIOS = {
    "FK (0.25% / 0.10%)": (0.0025, 0.0010),
    "FK (0.50% / 0.10%)": (0.0050, 0.0010),
    "FK (0.75% / 0.10%)": (0.0075, 0.0010),
    "FK (0.25% / 0.15%)": (0.0025, 0.0015),
    "FK (0.50% / 0.15%)": (0.0050, 0.0015),
    "FK (0.75% / 0.15%)": (0.0075, 0.0015),
    "FK (0.25% / 0.20%)": (0.0025, 0.0020),
    "FK (0.50% / 0.20%)": (0.0050, 0.0020),
    "FK (0.75% / 0.20%)": (0.0075, 0.0020),
    "FK (0.50% / 0.25%) [bisher bester]": (0.0050, 0.0025),
}


def block_bootstrap_daily(daily: pd.Series, block_days: int, n_sim: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Resamples `daily` (a return series) in contiguous blocks of
    `block_days`, with replacement, into n_sim synthetic paths of the same
    total length. Returns (max_dd_array, total_return_array)."""
    vals = daily.to_numpy()
    n = len(vals)
    n_blocks_needed = int(np.ceil(n / block_days))
    max_start = n - block_days
    max_dds = np.empty(n_sim)
    total_rets = np.empty(n_sim)
    for s in range(n_sim):
        starts = rng.integers(0, max_start + 1, size=n_blocks_needed)
        pieces = [vals[st:st + block_days] for st in starts]
        path = np.concatenate(pieces)[:n]
        equity = STARTING_EQUITY * np.cumprod(1 + path)
        equity = np.concatenate([[STARTING_EQUITY], equity])
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / peak
        max_dds[s] = dd.min()
        total_rets[s] = equity[-1] / STARTING_EQUITY - 1
    return max_dds, total_rets


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)

    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    cont_oos_sig = cont_sig[cont_sig.index >= SPLIT]
    cont_trades = simulate_trades(cont_oos_sig, CONT_BACKTEST_CFG)

    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)
    rev_oos_sig = rev_sig[rev_sig.index >= SPLIT]
    rev_trades = simulate_trades_concurrent(rev_oos_sig, REV_BACKTEST_CFG)

    rng = np.random.default_rng(RNG_SEED)

    for name, (risk_cont, risk_rev) in SCENARIOS.items():
        print("\n" + "=" * 100)
        print(f"{name}")
        print("=" * 100)
        sim = simulate_combined_account(
            {"continuation": cont_trades, "reversal": rev_trades},
            {"continuation": risk_cont, "reversal": risk_rev},
            MAX_CONCURRENT,
            starting_equity=STARTING_EQUITY,
        )
        daily = equity_curve_to_daily_returns(sim["equity_curve"], rev_oos_sig.index)
        realized_total = sim["final_equity"] / STARTING_EQUITY - 1
        realized_mdd = ((sim["equity_curve"]["equity"].to_numpy() / np.maximum.accumulate(sim["equity_curve"]["equity"].to_numpy())) - 1).min()
        print(f"Realisierter (historischer) Pfad: MaxDD={realized_mdd:.2%}  TotalReturn={realized_total:+.2%}  (n_trading_days={len(daily)})")

        max_dds, total_rets = block_bootstrap_daily(daily, BLOCK_DAYS, N_SIM, rng)
        print(f"\nBlock-Bootstrap ({N_SIM} simulierte Pfade, Blockgroesse={BLOCK_DAYS} Handelstage):")
        for p in (5, 10, 25, 50, 75, 90, 95):
            print(f"  P{p:>2} MaxDD={np.percentile(max_dds, p):>8.2%}   P{p:>2} TotalReturn={np.percentile(total_rets, p):>+9.2%}")
        breach_prob = (max_dds < -MAX_DD_LIMIT).mean()
        print(f"\n  P(MaxDD > {MAX_DD_LIMIT:.0%}) = {breach_prob:.1%}")
        print(f"  Median MaxDD = {np.median(max_dds):.2%}   Median TotalReturn = {np.median(total_rets):+.2%}")
        print(f"  Schlechtester simulierter Pfad: MaxDD={max_dds.min():.2%}")


if __name__ == "__main__":
    main()
