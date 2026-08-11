"""Diagnose cls_practical's SL/TP structure and hunt for a validating filter,
per the user's request (2026-08-11): win-rate is low (28.8%, ADR-TP mode) -
is that a badly-placed SL/TP, or the expected shape of a trend-following
asymmetric payoff (few big winners, many small losers)? And is there a
signal in the trade's own features (rates z-score strength, cross-pair
breadth, realised R:R, day-of-week/session) that separates winners from
losers before the fact?"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from presettle_breakout.data import fetch_m5_berlin
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def mfe_mae_r(eurusd_m5: pd.DataFrame, trade: pd.Series) -> tuple[float, float]:
    """Max favourable / adverse excursion (in R, R = sl_distance) between
    entry and exit, using M5 high/low (not just close) - how close did a
    losing trade get to profit before reversing, and how much drawdown did
    a winner sit through first?"""
    d = 1 if trade["direction"] == "long" else -1
    sl_dist = abs(trade["entry_price"] - trade["sl"])
    window = eurusd_m5.loc[trade["entry_time"] : trade["exit_time"]]
    if window.empty or sl_dist <= 0:
        return np.nan, np.nan
    if d == 1:
        mfe = (window["high"].max() - trade["entry_price"]) / sl_dist
        mae = (trade["entry_price"] - window["low"].min()) / sl_dist
    else:
        mfe = (trade["entry_price"] - window["low"].min()) / sl_dist
        mae = (window["high"].max() - trade["entry_price"]) / sl_dist
    return mfe, mae


def main():
    eurusd_m5 = fetch_m5_berlin("EURUSD", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, tp_mode="adr")

    trades["sl_dist"] = (trades["entry_price"] - trades["sl"]).abs()
    trades["tp_dist"] = (trades["entry_price"] - trades["tp"]).abs()
    trades["realised_rr"] = trades["tp_dist"] / trades["sl_dist"]
    trades["win"] = trades["exit_reason"] == "take_profit"

    mfe_mae = trades.apply(lambda t: mfe_mae_r(eurusd_m5, t), axis=1, result_type="expand")
    trades["mfe_r"], trades["mae_r"] = mfe_mae[0], mfe_mae[1]

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    print("=== 1) SL/TP-Struktur ===")
    print(trades[["sl_dist", "tp_dist", "realised_rr"]].describe())
    print(f"\nMedian realised R:R (TP-Distanz / SL-Distanz): {trades['realised_rr'].median():.2f}")
    print(f"Anteil Trades mit R:R >= 3: {(trades['realised_rr'] >= 3).mean():.1%}")

    print("\n=== 2) MFE/MAE - wie nah kamen Verlierer an den Gewinn? ===")
    losers = trades[~trades["win"]]
    winners = trades[trades["win"]]
    print(f"Verlierer (n={len(losers)}): Median MFE = {losers['mfe_r'].median():.2f}R, "
          f"Anteil die je >=0.5R Plus sahen: {(losers['mfe_r'] >= 0.5).mean():.1%}, "
          f"Anteil die je >=1.0R Plus sahen: {(losers['mfe_r'] >= 1.0).mean():.1%}")
    print(f"Gewinner (n={len(winners)}): Median MAE (Rückgang zuvor) = {winners['mae_r'].median():.2f}R")

    print("\n=== 3) Kandidaten-Filter: trennen sie Gewinner von Verlierern? ===")
    print("\n-- nach Setup --")
    print(trades.groupby("setup")["win"].agg(["count", "mean"]))
    print("\n-- nach Richtung --")
    print(trades.groupby("direction")["win"].agg(["count", "mean"]))
    print("\n-- nach Wochentag --")
    trades["weekday"] = trades["entry_time"].dt.day_name()
    print(trades.groupby("weekday")["win"].agg(["count", "mean"]))
    print("\n-- nach Haltedauer-Terzil (hold_bars) --")
    trades["hold_tercile"] = pd.qcut(trades["hold_bars"], 3, labels=["kurz", "mittel", "lang"], duplicates="drop")
    print(trades.groupby("hold_tercile", observed=True)["win"].agg(["count", "mean"]))
    print("\n-- nach SL-Distanz-Terzil (eng/mittel/weit) --")
    trades["sl_tercile"] = pd.qcut(trades["sl_dist"], 3, labels=["eng", "mittel", "weit"], duplicates="drop")
    print(trades.groupby("sl_tercile", observed=True)["win"].agg(["count", "mean"]))

    trades.to_parquet(Path(__file__).resolve().parents[1] / "data_cache" / "cls_practical" / "diagnosis_trades.parquet")
    print("\nGespeichert: data_cache/cls_practical/diagnosis_trades.parquet")


if __name__ == "__main__":
    main()
