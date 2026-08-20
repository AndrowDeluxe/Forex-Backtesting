"""Portfolio risk sizing (chat 2026-08-20): "FK Challenge IQ Markets" -
max 6% (Gesamt-)Drawdown, max 1% Risiko pro Position, Ziel +8% Return; vs.
"EK" (Eigenkapital, eigenes Konto) - renditeoptimiert, hoeheres Risiko ok.

Both strategies' OOS trades (already IS/OOS-validated - this script does
NOT touch signal generation, only how much is risked per trade, so no
IS/OOS split is needed here: position sizing is a deterministic transform
of an already-fixed trade sequence, not a new source of curve-fitting)
are run through ONE shared account equity pool via gold_smc_htf_ltf.
concurrent_backtest.simulate_combined_account - risk_pct per strategy IS
the "weighting" knob here (a strategy risking more per trade gets more of
the shared risk budget), since both draw from and return to the SAME real
balance, which is how a real funded account actually works (not two
walled-off capital sleeves).

Caveat stated explicitly: MaxDD/return figures below come from ONE
historical OOS year (2025-08 to 2026-08) - a single draw, not a
guarantee. Recommend headroom under the 6% hard limit, not cutting it to
the wire.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import simulate_combined_account, simulate_trades_concurrent
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
STARTING_EQUITY = 100_000.0
TARGET_RETURN = 0.08
MAX_DD_LIMIT = 0.06

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)

REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)

MAX_CONCURRENT = {"continuation": None, "reversal": 3}  # continuation is inherently single-position already


def event_max_drawdown(equity_curve: pd.DataFrame) -> float:
    eq = equity_curve["equity"].to_numpy()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def time_to_target(equity_curve: pd.DataFrame, starting_equity: float, target_return: float):
    eq = equity_curve["equity"].to_numpy()
    times = equity_curve["time"].to_numpy()
    hit = eq >= starting_equity * (1 + target_return)
    if not hit.any():
        return None
    i = int(np.argmax(hit))
    days = (pd.Timestamp(times[i]) - pd.Timestamp(times[0])).days
    return days


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

    print(f"Continuation OOS trades: {len(cont_trades)}   Reversal-Kaskade OOS raw candidates: {len(rev_trades)}")

    def run_combo(risk_cont: float, risk_rev: float) -> dict:
        sim = simulate_combined_account(
            {"continuation": cont_trades, "reversal": rev_trades},
            {"continuation": risk_cont, "reversal": risk_rev},
            MAX_CONCURRENT,
            starting_equity=STARTING_EQUITY,
        )
        mdd = event_max_drawdown(sim["equity_curve"])
        total_ret = sim["final_equity"] / STARTING_EQUITY - 1
        days = time_to_target(sim["equity_curve"], STARTING_EQUITY, TARGET_RETURN)
        return {"risk_cont": risk_cont, "risk_rev": risk_rev, "n_taken": sim["n_taken"], "n_skipped": sim["n_skipped"],
                "max_dd": mdd, "total_return": total_ret, "final_equity": sim["final_equity"], "days_to_target": days}

    print("\n" + "=" * 100)
    print(f"1. FK CHALLENGE IQ MARKETS - max_dd<={MAX_DD_LIMIT:.0%}, max risk/position<=1%, Ziel={TARGET_RETURN:.0%}")
    print("=" * 100)
    fk_grid = [0.0025, 0.005, 0.0075, 0.01]
    fk_rows = [run_combo(rc, rr) for rc in fk_grid for rr in fk_grid]
    fk_df = pd.DataFrame(fk_rows)
    fk_df["compliant"] = fk_df["max_dd"].abs() <= MAX_DD_LIMIT
    fk_df["days_to_target"] = fk_df["days_to_target"].apply(lambda d: d if d is not None else np.nan)
    print(fk_df.to_string(index=False, formatters={
        "risk_cont": "{:.2%}".format, "risk_rev": "{:.2%}".format, "max_dd": "{:.2%}".format,
        "total_return": "{:+.2%}".format, "final_equity": "${:,.0f}".format,
    }))

    compliant = fk_df[fk_df["compliant"]]
    if not compliant.empty:
        reached = compliant[compliant["days_to_target"].notna()]
        pick_pool = reached if not reached.empty else compliant
        best_fk = pick_pool.sort_values(["days_to_target", "total_return"], ascending=[True, False]).iloc[0] if not reached.empty else pick_pool.sort_values("total_return", ascending=False).iloc[0]
        print(f"\nEmpfehlung FK Challenge: risk_cont={best_fk['risk_cont']:.2%}  risk_rev={best_fk['risk_rev']:.2%}")
        print(f"  -> MaxDD={best_fk['max_dd']:.2%}  TotalReturn={best_fk['total_return']:+.2%}  Tage bis +{TARGET_RETURN:.0%}: {best_fk['days_to_target']}")

    print("\n" + "=" * 100)
    print("2. EK (EIGENKAPITAL) - renditeoptimiert, kein hartes DD-Limit")
    print("=" * 100)
    ek_grid = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    ek_rows = [run_combo(rc, rr) for rc in ek_grid for rr in ek_grid]
    ek_df = pd.DataFrame(ek_rows)
    ek_df["days_to_target"] = ek_df["days_to_target"].apply(lambda d: d if d is not None else np.nan)
    top_ek = ek_df.sort_values("total_return", ascending=False).head(10)
    print("Top 10 nach TotalReturn:")
    print(top_ek.to_string(index=False, formatters={
        "risk_cont": "{:.2%}".format, "risk_rev": "{:.2%}".format, "max_dd": "{:.2%}".format,
        "total_return": "{:+.2%}".format, "final_equity": "${:,.0f}".format,
    }))

    print("\n" + "=" * 100)
    print("3. AKTUELLER 'STANDARD' ZUM VERGLEICH: 1.0% Risk fuer beide")
    print("=" * 100)
    std = run_combo(0.01, 0.01)
    print(f"  risk_cont=1.00%  risk_rev=1.00%  MaxDD={std['max_dd']:.2%}  TotalReturn={std['total_return']:+.2%}  Tage bis +{TARGET_RETURN:.0%}: {std['days_to_target']}")

    print("\n" + "=" * 100)
    print("4. FINALE ENTSCHEIDUNGEN (chat 2026-08-20)")
    print("=" * 100)
    fk_final = run_combo(0.01, 0.0025)
    print(f"  FK Challenge gewaehlt: risk_cont=1.00%  risk_rev=0.25%  MaxDD={fk_final['max_dd']:.2%}  TotalReturn={fk_final['total_return']:+.2%}  Tage bis +{TARGET_RETURN:.0%}: {fk_final['days_to_target']}")
    ek_final = run_combo(0.02, 0.015)
    print(f"  EK gewaehlt:           risk_cont=2.00%  risk_rev=1.50%  MaxDD={ek_final['max_dd']:.2%}  TotalReturn={ek_final['total_return']:+.2%}  Tage bis +{TARGET_RETURN:.0%}: {ek_final['days_to_target']}")


if __name__ == "__main__":
    main()
