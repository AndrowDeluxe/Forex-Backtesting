"""Research script: realistic reconstruction + honest test of the 3 FLPD-
paper building blocks (ssrn-6880798, "Multifractal Price Delivery in
Algorithmic Futures Markets") on real Binance data - NOT a reproduction of
the paper's own headline numbers (those need Level-3 order-book tick data
and a 4.7-second HFT execution window this repo does not have and could not
realistically execute against anyway). See resources/crypto-hurst-wyckoff-
cycles.md for the full paper distillation and every proxy/simplification
decision's rationale.

Baustein 1 (crypto_flpd.hurst) - dynamic Hurst exponent via DFA-2, testable
1:1 with real bar data.
Baustein 2 (crypto_flpd.liquidity) - Temporal-Liquidity-Vacuum PROXY (real
n_trades thinness + Corwin-Schultz spread widening, no order book exists).
Baustein 3 (crypto_flpd.phases) - Psi multiscale delivery matrix, AD-phase
completions taken from the already-validated EMA9/21 signal instead of the
paper's Baum-Welch HMM.

Structure:
  0. Premise check (cheap, first): does BTC even show the paper's claimed
     scale-invariant Hurst signature (H approx 0.6-0.7 across 15m/1h/4h/1d)?
  Phase A: Hurst-collapse (Baustein 1) as an extra EXIT overlay on the
     already-validated btc_ema_cross EMA9/21 Daily baseline - answers the
     open crash-/trend-end-filter question from resources/trend-following-
     momentum.md (Nachtrag 2026-08-14 (5): ATR-expansion, BTC-ETH
     correlation, and taker-delta all failed at this).
  Phase B: the full Psi-threshold strategy (all 3 Bausteine together),
     1h entries fed by 4h AD-phase completions, exits on Hurst collapse.
Both phases run on BTCUSDT (primary) and ETHUSDT (paper's own robustness
check #1: cross-asset, same code, no re-tuning). Structure-preserving
randomization tests (asian_range_breakout.randomization's shuffle
primitives, reused via crypto_flpd.significance) are run on BTCUSDT; ETHUSDT
gets the point-estimate comparison only, to keep total runtime bounded (each
resimulation-based test re-runs the full bar-by-bar loop hundreds of times)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import simulate_ema_cross
from crypto_flpd.engine import simulate_ema_cross_with_hurst_exit, simulate_flpd
from crypto_flpd.hurst import dfa_hurst, hurst_collapse_signal, rolling_hurst
from crypto_flpd.liquidity import liquidity_weight
from crypto_flpd.phases import completion_signal, psi_matrix
from crypto_flpd.significance import signal_timing_significance

FULL_START = "2017-08-17"  # BTCUSDT Binance listing date; earlier than ETHUSDT's own listing, fetch_klines just returns what exists
END = "2026-08-25"
SPLIT = pd.Timestamp("2023-12-01", tz="UTC")  # same IS/OOS boundary as scripts/research_ema_9_21_cross_btc.py

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
PREMISE_RESOLUTIONS = ["15m", "1h", "4h", "1d"]
N_SHUFFLES = 300


def fmt(m: dict, label: str) -> str:
    return (
        f"{label:<28} n={m['n_trades']:>4}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.3f}  "
        f"TotalReturn={m['total_return']:+.1%}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}"
    )


def report_significance(name: str, result: dict):
    print(f"\n  --- significance: {name} ---")
    print(f"    actual: n_trades={result['actual_n_trades']}  PF={result['actual_profit_factor']:.3f}")
    for method in ("rotation", "run_permutation"):
        r = result[method]
        print(
            f"    [{method:>15}] null PF mean={r['null_mean']:.3f} std={r['null_std']:.3f} "
            f"[p05={r['null_p05']:.3f}, p95={r['null_p95']:.3f}]  p-value(null>=actual)={r['p_value']:.3f}  "
            f"(n_valid={r['n_valid_shuffles']}/{N_SHUFFLES})"
        )


# ---------------------------------------------------------------------------
# 0. Premise check
# ---------------------------------------------------------------------------

def premise_check(symbol: str):
    print("\n" + "=" * 88)
    print(f"0. PREMISE CHECK - does {symbol} show the paper's claimed scale-invariant Hurst signature?")
    print("=" * 88)
    rows = []
    for interval in PREMISE_RESOLUTIONS:
        t0 = time.time()
        df = fetch_klines(symbol, interval, FULL_START, END)
        log_ret = np.log(df["close"]).diff().dropna().to_numpy()
        global_h = dfa_hurst(log_ret)

        ht = rolling_hurst(df["close"], window=500, step=max(len(df) // 3000, 1))
        ht_valid = ht.dropna()
        rows.append(
            {
                "interval": interval, "n_bars": len(df),
                "global_H": global_h,
                "rolling_H_mean": ht_valid.mean() if len(ht_valid) else float("nan"),
                "rolling_H_std": ht_valid.std() if len(ht_valid) else float("nan"),
                "fetch_and_compute_s": round(time.time() - t0, 1),
            }
        )
        print(f"  {interval:<5} {len(df):>7} bars  global_H={global_h:.3f}  "
              f"rolling_H mean={rows[-1]['rolling_H_mean']:.3f} std={rows[-1]['rolling_H_std']:.3f}  "
              f"({rows[-1]['fetch_and_compute_s']}s)")

    table = pd.DataFrame(rows)
    spread = table["global_H"].max() - table["global_H"].min()
    print(
        f"\n  Paper's claim (Table 3): H approx 0.62-0.71, roughly constant 5min->Daily.\n"
        f"  Observed global_H spread across scales: {spread:.3f} "
        f"({'CONSISTENT with the paper' if spread < 0.10 else 'WIDER than the paper reports - premise weaker on this data'})."
    )
    return table


# ---------------------------------------------------------------------------
# Phase A: Hurst-collapse exit overlay on the existing EMA9/21 Daily baseline
# ---------------------------------------------------------------------------

def phase_a(symbol: str, run_significance: bool):
    print("\n" + "=" * 88)
    print(f"PHASE A ({symbol}, Daily) - Hurst-collapse exit overlay on the validated EMA9/21 baseline")
    print("=" * 88)
    daily = fetch_klines(symbol, "1d", FULL_START, END)

    ht = rolling_hurst(daily["close"], window=500, step=5)
    collapse = hurst_collapse_signal(ht, z_window=50, z_thresh=2.0)
    print(f"  {len(daily)} daily bars, {collapse.sum()} Hurst-collapse events flagged "
          f"({collapse.sum() / max((~ht.isna()).sum(), 1):.2%} of bars with a valid H^T).")

    windows = [("Full", None), ("IS (< 2023-12-01)", None), ("OOS (>= 2023-12-01)", SPLIT)]
    for label, sim_from in windows:
        if label.startswith("IS"):
            part = daily[daily.index < SPLIT]
            baseline = simulate_ema_cross(part, 9, 21)
            overlay = simulate_ema_cross_with_hurst_exit(part, 9, 21, collapse[collapse.index < SPLIT])
        else:
            baseline = simulate_ema_cross(daily, 9, 21, sim_from=sim_from)
            overlay = simulate_ema_cross_with_hurst_exit(daily, 9, 21, collapse, sim_from=sim_from)
        print(fmt(baseline, f"  {label} EMA9/21 baseline:"))
        print(fmt(overlay, f"  {label} + Hurst exit:"))
        print(f"    exit reasons (overlay): {overlay['exit_reason_counts']}")

    if run_significance:
        def _sim(shuffled_collapse: pd.Series) -> dict:
            return simulate_ema_cross_with_hurst_exit(daily, 9, 21, shuffled_collapse, sim_from=None)

        result = signal_timing_significance(collapse.fillna(False), _sim, n_shuffles=N_SHUFFLES, seed=7)
        report_significance("Hurst-collapse exit timing vs. same-footprint random exit timing (Full history)", result)

    return {"collapse": collapse}


# ---------------------------------------------------------------------------
# Phase B: full Psi-threshold strategy
# ---------------------------------------------------------------------------

def phase_b(symbol: str, run_significance: bool):
    print("\n" + "=" * 88)
    print(f"PHASE B ({symbol}, 1h entries / 4h AD-phase completions) - full Psi strategy")
    print("=" * 88)
    ltf = fetch_klines(symbol, "1h", FULL_START, END)
    htf = fetch_klines(symbol, "4h", FULL_START, END)
    print(f"  {len(ltf)} 1h bars, {len(htf)} 4h bars.")

    htf_completion = completion_signal(htf["close"], fast=9, slow=21)
    htf_liq_weight = liquidity_weight(htf["n_trades"], htf["high"], htf["low"], window=30 * 6)  # 30 days on 4h bars
    ht_1h = rolling_hurst(ltf["close"], window=500, step=24)
    collapse_1h = hurst_collapse_signal(ht_1h, z_window=50, z_thresh=2.0)

    is_htf_mask = htf.index < SPLIT
    print("  Grid-searching decay_lambda on IS-only data (train-only, no OOS peeking) ...")
    best_lambda, best_pf = None, -np.inf
    for decay_lambda in (0.01, 0.05, 0.1, 0.2):
        psi_is = psi_matrix(
            htf_completion[is_htf_mask], htf_bar_duration=pd.Timedelta("4h"),
            ltf_index=ltf.index[ltf.index < SPLIT],
            liquidity_weight=htf_liq_weight[is_htf_mask], decay_lambda=decay_lambda, lookback_bars=42,
        )
        is_ltf = ltf[ltf.index < SPLIT]
        m = simulate_flpd(is_ltf, psi_is, collapse_1h[collapse_1h.index < SPLIT], entry_window=30 * 24)
        print(f"    lambda={decay_lambda:<5} IS: n={m['n_trades']:>4}  PF={m['profit_factor']:.3f}  CAGR={m['cagr']:+.1%}")
        if m["n_trades"] >= 10 and m["profit_factor"] > best_pf:
            best_lambda, best_pf = decay_lambda, m["profit_factor"]
    if best_lambda is None:
        best_lambda = 0.1
        print(f"  No lambda produced >=10 IS trades - falling back to default lambda={best_lambda}.")
    else:
        print(f"  Selected decay_lambda={best_lambda} (best IS-only PF={best_pf:.3f}).")

    psi_full = psi_matrix(
        htf_completion, htf_bar_duration=pd.Timedelta("4h"), ltf_index=ltf.index,
        liquidity_weight=htf_liq_weight, decay_lambda=best_lambda, lookback_bars=42,
    )

    windows = [("Full", ltf, None), ("IS (< 2023-12-01)", ltf[ltf.index < SPLIT], None), ("OOS (>= 2023-12-01)", ltf, SPLIT)]
    last_full_result = None
    for label, part, sim_from in windows:
        if label.startswith("IS"):
            psi_part = psi_full[psi_full.index < SPLIT]
            collapse_part = collapse_1h[collapse_1h.index < SPLIT]
            result = simulate_flpd(part, psi_part, collapse_part, entry_window=30 * 24)
        else:
            result = simulate_flpd(part, psi_full, collapse_1h, entry_window=30 * 24, sim_from=sim_from)
        print(fmt(result, f"  {label} FLPD (lambda={best_lambda}):"))
        if not result["trades"].empty:
            print(f"    exit reasons: {result['trades']['exit_reason'].value_counts().to_dict()}")
        if label == "Full":
            last_full_result = result

    if run_significance and last_full_result is not None:
        def _sim(shuffled_entry: pd.Series) -> dict:
            return simulate_flpd(
                ltf, psi_full, collapse_1h, entry_window=30 * 24, entry_target_override=shuffled_entry
            )

        result = signal_timing_significance(
            last_full_result["entry_target"], _sim, n_shuffles=N_SHUFFLES, seed=11
        )
        report_significance("Psi entry timing vs. same-footprint random entry timing (Full history)", result)

    return {"lambda": best_lambda, "psi": psi_full, "hurst_collapse": collapse_1h}


def main():
    t_start = time.time()
    premise_check("BTCUSDT")

    for symbol in SYMBOLS:
        phase_a(symbol, run_significance=(symbol == "BTCUSDT"))

    for symbol in SYMBOLS:
        phase_b(symbol, run_significance=(symbol == "BTCUSDT"))

    print(f"\nTotal runtime: {(time.time() - t_start) / 60:.1f} min.")


if __name__ == "__main__":
    main()
