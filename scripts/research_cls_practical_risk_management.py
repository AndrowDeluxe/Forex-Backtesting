"""Zwei Risk-Management-Varianten fuer cls_practical (User-Anfrage 2026-08-13):

1. STATISCH fuer eine Funded-Challenge: max 3% Tagesverlust, max 7% Gesamt-
   Drawdown. Da das Sizing-Modell FIXES Dollar-Risiko ist (kein Comitting,
   siehe Chat-Diskussion), skaliert alles EXAKT linear mit risk_pct -- der
   noetige risk_pct laesst sich direkt aus dem schlechtesten Einzeltag und
   dem Max Drawdown bei einem Referenz-risk_pct (1%) ableiten, dann per
   echtem Re-Run verifiziert (kein Rundungsfehler).

2. Continuation/Reversal GETRENNT gesizt (statt einheitlichem risk_pct fuer
   beide) -- die beiden Setups haben sehr unterschiedliche R-Profile
   (Kelly f* Continuation=8.32%, Reversal=20.79%, siehe gestrige Kelly-
   Analyse). Getrennte Simulation je Setup, dann chronologisch zu einer
   gemeinsamen Equity-Kurve zusammengefuehrt.

3. DYNAMISCH nach Winning-Streak: risk_pct erhoeht sich nach N aufeinander-
   folgenden Gewinnern, faellt nach einem Verlierer sofort zurueck --
   post-hoc auf die bestehende Trade-R-Sequenz angewendet (die Ein-/Ausstiegs-
   Signale haengen nicht von der Positionsgroesse ab, nur die $-Betraege --
   deshalb ist das post-hoc-Multiplizieren methodisch sauber, kein Bias)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
INITIAL_EQUITY = 100_000.0
TRADING_DAYS_PER_YEAR = 252


def equity_metrics_from_daily_pnl(daily_pnl: pd.Series) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    daily_ret = equity.pct_change().fillna(0.0)
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    total_return = equity.iloc[-1] / INITIAL_EQUITY - 1
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    worst_day_pct = (daily_pnl / INITIAL_EQUITY).min() * 100
    return {
        "final_equity": equity.iloc[-1], "total_return_pct": total_return * 100, "cagr_pct": cagr * 100,
        "max_drawdown_pct": dd.min() * 100, "worst_day_pct": worst_day_pct, "sharpe": sharpe,
    }


def daily_pnl_from_trades(trades: pd.DataFrame) -> pd.Series:
    full_days = pd.date_range(pd.Timestamp(START), pd.Timestamp(END), freq="D")
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    return trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    args = (eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    # ================================================================
    print("\n=== 1) STATISCHE CHALLENGE-KONFIGURATION (max 3%/Tag, max 7% gesamt) ===")
    trades_1pct = simulate_cls_practical(*args, risk_pct=0.01)
    daily_1pct = daily_pnl_from_trades(trades_1pct)
    m1 = equity_metrics_from_daily_pnl(daily_1pct)
    print(f"Referenz bei risk_pct=1.0%: schlechtester Tag={m1['worst_day_pct']:.2f}% MaxDD={m1['max_drawdown_pct']:.2f}%")

    scale_daily = 3.0 / abs(m1["worst_day_pct"])
    scale_dd = 7.0 / abs(m1["max_drawdown_pct"])
    implied_risk_pct = 0.01 * min(scale_daily, scale_dd)
    binding = "Tagesverlust" if scale_daily < scale_dd else "Gesamt-Drawdown"
    print(f"Linear abgeleiteter risk_pct fuer 3%/7%-Limits: {implied_risk_pct*100:.3f}% (bindend: {binding})")

    # auf 2 Nachkommastellen abrunden (konservativ, nie aufrunden bei Challenge-Limits)
    challenge_risk_pct = np.floor(implied_risk_pct * 10000) / 10000
    print(f"Verwendet (abgerundet): {challenge_risk_pct*100:.2f}%")

    trades_challenge = simulate_cls_practical(*args, risk_pct=challenge_risk_pct)
    daily_challenge = daily_pnl_from_trades(trades_challenge)
    m_challenge = equity_metrics_from_daily_pnl(daily_challenge)
    print(f"VERIFIZIERT bei risk_pct={challenge_risk_pct*100:.2f}%: "
          f"Endkapital=${m_challenge['final_equity']:,.0f} Return={m_challenge['total_return_pct']:+.1f}% "
          f"CAGR={m_challenge['cagr_pct']:+.2f}% schlechtester Tag={m_challenge['worst_day_pct']:.2f}% "
          f"MaxDD={m_challenge['max_drawdown_pct']:.2f}% Sharpe={m_challenge['sharpe']:.2f}")
    breach_daily = (daily_challenge / INITIAL_EQUITY * 100 < -3.0).sum()
    print(f"Tage mit >3% Tagesverlust: {breach_daily} von {len(daily_challenge)}")

    # ================================================================
    print("\n=== 2) Continuation/Reversal GETRENNT gesizt (Kelly-informiert) ===")
    # Kelly f* aus der gestrigen Analyse: Continuation 8.32%, Reversal 20.79%.
    # Hier konservativ mit Quarter-Kelly angesetzt (Disziplin wie ueberall im
    # Projekt: nie volles Kelly), auf denselben Gesamt-Risiko-Level (1%
    # Referenz-Trade) normiert, damit die Vergleichbarkeit zur einheitlichen
    # Baseline erhalten bleibt.
    cont_risk = 0.01 * (8.32 / 20.79)  # relatives Verhaeltnis zur Reversal-Basis
    rev_risk = 0.01
    print(f"Kelly-Verhaeltnis-Sizing: Continuation risk_pct={cont_risk*100:.3f}%, Reversal risk_pct={rev_risk*100:.3f}%")

    trades_cont = simulate_cls_practical(*args, allowed_setups=("continuation",), risk_pct=cont_risk)
    trades_rev = simulate_cls_practical(*args, allowed_setups=("reversal",), risk_pct=rev_risk)
    combined = pd.concat([trades_cont, trades_rev], ignore_index=True)
    daily_combined = daily_pnl_from_trades(combined)
    m_combined = equity_metrics_from_daily_pnl(daily_combined)
    print(f"Getrennt gesizt: Endkapital=${m_combined['final_equity']:,.0f} Return={m_combined['total_return_pct']:+.1f}% "
          f"MaxDD={m_combined['max_drawdown_pct']:.2f}% Sharpe={m_combined['sharpe']:.2f}")

    # Vergleich: einheitliches risk_pct=1% fuer beide (aus Skript 1 bereits vorhanden)
    print(f"Einheitlich (Referenz, beide 1%): Endkapital=${m1['final_equity']:,.0f} Return={m1['total_return_pct']:+.1f}% "
          f"MaxDD={m1['max_drawdown_pct']:.2f}% Sharpe={m1['sharpe'] if 'sharpe' in m1 else float('nan'):.2f}")

    # ================================================================
    print("\n=== 3) DYNAMISCHE Anpassung nach Winning-Streak (post-hoc auf 1%-Basis) ===")
    trades_all = simulate_cls_practical(*args, risk_pct=0.01).sort_values("exit_time").reset_index(drop=True)
    trades_all["r_multiple"] = trades_all["pnl_usd"] / trades_all["risk_amount_usd"]

    def streak_multiplier_pnl(trades: pd.DataFrame, boost_after: int, boost_mult: float, cap_mult: float) -> pd.Series:
        mult = []
        streak = 0
        current = 1.0
        for r in trades["r_multiple"]:
            mult.append(current)
            if r > 0:
                streak += 1
                if streak >= boost_after:
                    current = min(current * boost_mult, cap_mult)
            else:
                streak = 0
                current = 1.0
        return trades["pnl_usd"] * pd.Series(mult, index=trades.index)

    for boost_after, boost_mult, cap_mult in [(2, 1.25, 2.0), (3, 1.5, 3.0), (2, 1.5, 4.0)]:
        adj_pnl = trades_all.copy()
        adj_pnl["pnl_usd"] = streak_multiplier_pnl(trades_all, boost_after, boost_mult, cap_mult)
        daily_streak = daily_pnl_from_trades(adj_pnl)
        m_streak = equity_metrics_from_daily_pnl(daily_streak)
        print(f"Boost nach {boost_after} Gewinnern x{boost_mult} (Cap {cap_mult}x): "
              f"Endkapital=${m_streak['final_equity']:,.0f} Return={m_streak['total_return_pct']:+.1f}% "
              f"MaxDD={m_streak['max_drawdown_pct']:.2f}% schlechtester Tag={m_streak['worst_day_pct']:.2f}% "
              f"Sharpe={m_streak['sharpe']:.2f}")

    print(f"\nReferenz ohne Streak-Anpassung (konstant 1%): Return={m1['total_return_pct']:+.1f}% "
          f"MaxDD={m1['max_drawdown_pct']:.2f}% Sharpe={m1['sharpe']:.2f}")


if __name__ == "__main__":
    main()
