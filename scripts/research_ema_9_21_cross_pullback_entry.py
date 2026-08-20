"""BTC EMA9/21: Pullback-Entry-Test, angestossen 2026-08-20 nach einem
Bug-Fund in BTC-EMA-Cross-Bridge/executor_mt5.py: der Pending-Order-
Fallback dort jagte dem Kurs mit einem Buy Stop hinterher statt (wie
OU-Modell-MT5-Bridge/executor.py::_place_pending_entry es korrekt macht)
einen Pullback zum urspruenglichen Signal-Preis abzuwarten. Frage des
Users: laesst sich dasselbe Prinzip nicht nur als Exekutions-Fallback,
sondern als STRATEGIE selbst nutzen - auf einen Pullback zum EMA9 warten,
statt sofort beim Breakout zu kaufen?

Testet simulate_pullback_entry (btc_ema_cross/optimization.py) gegen die
Baseline simulate_risk_sized (btc_ema_cross/engine.py) ueber dieselbe
IS/OOS-Aufteilung wie der Rest dieses Research-Threads. Pullback-Fenster
3/5/10/15/20 Tage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, simulate_risk_sized
from btc_ema_cross.optimization import simulate_pullback_entry

FULL_START = "2017-08-17"
END = "2026-08-20"
IS_FRACTION = 0.7
STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01
WINDOWS_TO_TEST = [3, 5, 10, 15, 20]


def main():
    print(f"Fetching BTCUSDT daily {FULL_START} -> {END} ...")
    full = fetch_klines("BTCUSDT", "1d", FULL_START, END)
    split_i = int(len(full) * IS_FRACTION)
    oos_split_date = full.index[split_i]
    windows = [("IS", None), ("OOS", oos_split_date)]

    print("\n" + "=" * 90)
    print("PULLBACK-ENTRY (Buy-Limit auf EMA9 statt Market-Entry beim Breakout-Open)")
    print("=" * 90)
    for label, sim_from in windows:
        part = full if sim_from is not None else full.iloc[:split_i]
        m_base = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        print(f"\n  {label}:")
        print(f"    Baseline (sofort)   : n={m_base['n_trades']:>3}  WinRate={m_base['win_rate']:.1%}  "
              f"PF={m_base['profit_factor']:.2f}  CAGR={m_base['cagr']:+.1%}  MaxDD={m_base['max_dd']:.1%}  "
              f"WorstDay={m_base['worst_day_pct']:+.2f}%")
        for w in WINDOWS_TO_TEST:
            m = simulate_pullback_entry(part, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT,
                                         pullback_window=w, sim_from=sim_from)
            print(f"    Pullback {w:>2}d-Fenster: n={m['n_trades']:>3}  (verpasst={m['n_missed']:>3})  "
                  f"WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  CAGR={m['cagr']:+.1%}  "
                  f"MaxDD={m['max_dd']:.1%}  WorstDay={m['worst_day_pct']:+.2f}%")


if __name__ == "__main__":
    main()
