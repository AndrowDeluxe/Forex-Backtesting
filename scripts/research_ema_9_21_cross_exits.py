"""BTC EMA9/21: exit-logic deep dive requested 2026-08-15 - how much return
does the take-profit logic actually give up (precise IS/OOS table), a
proper breakeven-trigger sweep (0.25R-2.0R, not just one value), an
ATR-based TRAILING stop (Chandelier Exit) as an alternative to a fixed
take-profit, and a volume-exhaustion exit. An ETF-inflow-based exit was
also asked about - not implemented, see the note at the bottom (no data
source in this repo).

Helpers live in btc_ema_cross/optimization.py so the dashboard reuses the
exact tested implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, simulate_risk_sized
from btc_ema_cross.optimization import (
    simulate_asymmetric_short,
    simulate_chandelier_exit,
    simulate_volume_exhaustion_exit,
    simulate_with_tp_and_filters,
)

FULL_START = "2017-08-17"
END = "2026-08-13"
IS_FRACTION = 0.7
STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01


def main():
    print(f"Fetching BTCUSDT daily {FULL_START} -> {END} ...")
    full = fetch_klines("BTCUSDT", "1d", FULL_START, END)
    split_i = int(len(full) * IS_FRACTION)
    is_df, oos_split_date = full.iloc[:split_i], full.index[split_i]
    windows = [("IS", is_df, None), ("OOS", full, oos_split_date)]

    print("\n" + "=" * 78)
    print("1. RENDITE-VERSCHENKT-TABELLE (TP vs. kein TP)")
    print("=" * 78)
    for label, part, sim_from in windows:
        m_notp = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        print(f"\n  {label}: Kein TP CAGR={m_notp['cagr']:+.1%}  EndEquity=${m_notp['end_equity']:,.0f}")
        for tp in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            m = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, tp_r_mult=tp, sim_from=sim_from)
            pct_captured = m["end_equity"] / m_notp["end_equity"] * 100 if m_notp["end_equity"] > 0 else float("nan")
            print(f"    TP={tp}R: CAGR={m['cagr']:+.1%}  EndEquity=${m['end_equity']:,.0f}  ({pct_captured:.0f}% vom Kein-TP-Endkapital)")

    print("\n" + "=" * 78)
    print("2. BREAKEVEN-SWEEP (0.25R bis 2.0R)")
    print("=" * 78)
    for label, part, sim_from in windows:
        m0 = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, be_trigger_r=None, sim_from=sim_from)
        print(f"\n  {label}: Kein BE: n={m0['n_trades']:>3}  WinRate={m0['win_rate']:.1%}  PF={m0['profit_factor']:.2f}  CAGR={m0['cagr']:+.1%}  MaxDD={m0['max_dd']:.1%}")
        for be in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
            m = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, be_trigger_r=be, sim_from=sim_from)
            print(f"    BE@{be}R: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("3. CHANDELIER-TRAILING-STOP (hoechster Close seit Entry - Mult x ATR)")
    print("=" * 78)
    for label, part, sim_from in windows:
        print(f"\n  {label}:")
        for mult in [2.0, 2.5, 3.0, 3.5, 4.0]:
            m = simulate_chandelier_exit(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, mult, sim_from=sim_from)
            print(f"    Chandelier {mult}x: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("4. VOLUMEN-EXHAUSTION-EXIT (Vol < X% des 20d-Schnitts UND unrealisiert >= Y R)")
    print("=" * 78)
    for label, part, sim_from in windows:
        print(f"\n  {label}:")
        for thresh in [0.3, 0.5, 0.7]:
            for minr in [0.5, 1.0]:
                m = simulate_volume_exhaustion_exit(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, 20, thresh, minr, sim_from=sim_from)
                print(f"    VolRatio<{thresh}, ab {minr}R: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("5. KLEINE GEGENPOSITION AM CROSSUNDER (statt Flat)")
    print("=" * 78)
    for label, part, sim_from in windows:
        print(f"\n  {label}:")
        m0 = simulate_asymmetric_short(part, STARTING_CAPITAL, RISK_PCT, 0.0, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        print(f"    Baseline (Flat): PF={m0['profit_factor']:.2f}  CAGR={m0['cagr']:+.1%}  MaxDD={m0['max_dd']:.1%}  EndEquity=${m0['end_equity']:,.0f}")
        for frac in [0.1, 0.25, 0.5, 0.75, 1.0]:
            m = simulate_asymmetric_short(part, STARTING_CAPITAL, RISK_PCT, frac, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
            print(f"    Short={frac}x: n_short={m['n_short']:>2}  ShortPnL=${m['short_pnl']:>+10,.0f}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}  EndEquity=${m['end_equity']:,.0f}")

    print(
        "\nETF-Inflow-Exit: NICHT getestet - keine echte Datenquelle fuer taegliche IBIT/FBTC-\n"
        "Netto-Flows in diesem Repo (nur eine Literatur-Notiz, knowledge/resources/crypto-etf-flows.md).\n"
        "Muesste neu angebunden werden (z.B. Farside Investors, SoSoValue, CoinGlass)."
    )


if __name__ == "__main__":
    main()
