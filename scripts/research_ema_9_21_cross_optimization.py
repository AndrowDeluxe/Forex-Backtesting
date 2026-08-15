"""BTC EMA9/21: deeper optimization pass requested 2026-08-15 - Kelly
sizing, dynamic/vol-scaled risk management, an ATR-stop-multiple sweep, a
take-profit test, and two regime filters (ADX, 200-day trend), all against
the SAME IS/OOS split and warmup-preserving contract used throughout this
research thread (see btc_ema_cross/engine.py). Everything here is honestly
reported including negative results - matches this repo's own discipline
(e.g. the Gold Asian-Range-Breakout page's SL/TP sweep, which found no
improvement over the source's default parameters either).

Simulation helpers live in btc_ema_cross/optimization.py so the dashboard
shares the exact same tested implementation as this script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, simulate_risk_sized
from btc_ema_cross.optimization import kelly_from_trades, simulate_dynamic_vol_scaled, simulate_with_tp_and_filters

FULL_START = "2017-08-17"
END = "2026-08-13"
IS_FRACTION = 0.7
STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01


def main():
    print(f"Fetching BTCUSDT daily {FULL_START} -> {END} ...")
    full = fetch_klines("BTCUSDT", "1d", FULL_START, END)
    split_i = int(len(full) * IS_FRACTION)
    oos_split_date = full.index[split_i]
    windows = [("IS", None), ("OOS", oos_split_date)]

    print("\n" + "=" * 78)
    print("1. KELLY-ANALYSE (auf den echten 1%-Risiko-Trades der Baseline)")
    print("=" * 78)
    for label, sim_from in windows:
        if label == "IS":
            m = simulate_risk_sized(full.iloc[:split_i], 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=None)
        else:
            m = simulate_risk_sized(full, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        k = kelly_from_trades(m["trades"], label)
        print(f"\n  {label}: n={k['n_trades']}  WinRate={k['win_rate']:.1%}  AvgWinR={k['avg_win_r']:+.2f}  "
              f"AvgLossR={k['avg_loss_r']:+.2f}  PayoffB={k['payoff_ratio_b']:.2f}")
        print(f"    Kelly f*={k['kelly_f']:.1%}  Half-Kelly={k['half_kelly_f']:.1%}  "
              f"Quarter-Kelly={k['quarter_kelly_f']:.1%}  (aktuell genutzt: {RISK_PCT:.1%})")

    print("\n" + "=" * 78)
    print("2. DYNAMISCHES/VOL-SKALIERTES RISK-SIZING (risk_pct * median(ATR60)/aktuellerATR, [0.5,1.5])")
    print("=" * 78)
    for label, sim_from in windows:
        part = full if sim_from is not None else full.iloc[:split_i]
        m_static = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        m_dyn = simulate_dynamic_vol_scaled(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT,
                                             vol_lookback=60, scale_min=0.5, scale_max=1.5, sim_from=sim_from)
        print(f"\n  {label}:")
        print(f"    Statisch 1%:     n={m_static['n_trades']:>3}  PF={m_static['profit_factor']:.2f}  "
              f"CAGR={m_static['cagr']:+.1%}  MaxDD={m_static['max_dd']:.1%}  WorstDay={m_static['worst_day_pct']:+.2f}%")
        print(f"    Vol-skaliert:    n={m_dyn['n_trades']:>3}  PF={m_dyn['profit_factor']:.2f}  "
              f"CAGR={m_dyn['cagr']:+.1%}  MaxDD={m_dyn['max_dd']:.1%}  WorstDay={m_dyn['worst_day_pct']:+.2f}%")

    print("\n" + "=" * 78)
    print("3. ATR-STOP-MULTIPLIKATOR-SWEEP (1.0x bis 3.5x)")
    print("=" * 78)
    for label, sim_from in windows:
        part = full if sim_from is not None else full.iloc[:split_i]
        print(f"\n  {label}:")
        for mult in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
            m = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, mult, sim_from=sim_from)
            print(f"    {mult}x ATR: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  "
                  f"CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("4. TAKE-PROFIT-TEST (0.5R bis 4R, vs. kein TP)")
    print("=" * 78)
    for label, sim_from in windows:
        part = full if sim_from is not None else full.iloc[:split_i]
        print(f"\n  {label}:")
        m_notp = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        print(f"    Kein TP  : n={m_notp['n_trades']:>3}  WinRate={m_notp['win_rate']:.1%}  PF={m_notp['profit_factor']:.2f}  CAGR={m_notp['cagr']:+.1%}  MaxDD={m_notp['max_dd']:.1%}")
        for tp in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            m = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, tp_r_mult=tp, sim_from=sim_from)
            print(f"    TP={tp}R   : n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("5. REGIME-FILTER: ADX(14)-Mindestwert und 200-Tage-SMA-Trendfilter")
    print("=" * 78)
    for label, sim_from in windows:
        part = full if sim_from is not None else full.iloc[:split_i]
        print(f"\n  {label}:")
        m_base = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        print(f"    Kein Filter      : n={m_base['n_trades']:>3}  WinRate={m_base['win_rate']:.1%}  PF={m_base['profit_factor']:.2f}  CAGR={m_base['cagr']:+.1%}  MaxDD={m_base['max_dd']:.1%}")
        for adx_min in [15, 20, 25]:
            m = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, adx_min=adx_min, sim_from=sim_from)
            print(f"    ADX>={adx_min:<9}: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")
        m_trend = simulate_with_tp_and_filters(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, trend_sma=200, sim_from=sim_from)
        print(f"    SMA200-Trend     : n={m_trend['n_trades']:>3}  WinRate={m_trend['win_rate']:.1%}  PF={m_trend['profit_factor']:.2f}  CAGR={m_trend['cagr']:+.1%}  MaxDD={m_trend['max_dd']:.1%}")


if __name__ == "__main__":
    main()
