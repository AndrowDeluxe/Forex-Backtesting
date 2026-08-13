"""Funnel diagnosis: at which stage do candidate days actually get dropped,
and how many trades survive to the end? Answers the user's question
(2026-08-11) "warum bekommen wir so wenig Trades" and doubles as a sanity
check that the cross-pair filter (compute_cross_confirmation) is still
wired in - every stage below is a real, counted gate, nothing silently
dropped."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical, trend_bias
from cls_practical.rates import classify_rates_ampel, compute_rate_support_score
from strategy.cls_advanced import PAIRS, compute_cross_confirmation, compute_daily_features, to_berlin

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def main():
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5)
    daily_by_pair = {"EURUSD": daily}
    for pair, df in other_majors_m15.items():
        daily_by_pair[pair] = compute_daily_features(df)
    cross_confirm = compute_cross_confirmation(daily_by_pair)["EURUSD"]

    berlin_idx = to_berlin(eurusd_m5.index)
    date_series = pd.Series(berlin_idx.date, index=eurusd_m5.index)
    daily_close = eurusd_m5["close"].groupby(date_series).last()
    trend = trend_bias(daily_close, sma_window=100)

    rate_score = compute_rate_support_score(bund_m5, ustbond_m5)
    rates_ampel = classify_rates_ampel(rate_score, daily["direction"], z_window=60, z_threshold=0.0)

    n_total_days = len(daily)
    n_clean_break = ((daily["direction"] != 0) & daily["holds_0915"].notna()).sum()

    rows_with_signals = 0
    n_continuation_candidates = 0
    n_reversal_candidates = 0
    for day, row in daily.iterrows():
        direction = row["direction"]
        holds = row["holds_0915"]
        if direction == 0 or pd.isna(holds):
            continue
        t_val = trend.get(day, np.nan)
        r_flag = rates_ampel.get(day, "gelb")
        c_val = cross_confirm.get(day, np.nan)
        if pd.isna(t_val) or pd.isna(c_val):
            continue
        rows_with_signals += 1
        if holds and t_val == direction and r_flag == "grün" and bool(c_val):
            n_continuation_candidates += 1
        elif (not holds) and t_val == -direction and r_flag == "rot" and not bool(c_val):
            n_reversal_candidates += 1

    trades_both = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    trades_continuation = trades_both[trades_both["setup"] == "continuation"]
    trades_reversal = trades_both[trades_both["setup"] == "reversal"]

    print(f"1) Handelstage im Fenster ({START} -> {END}):                  {n_total_days}")
    print(f"2) ... mit sauberem Break im Settle-Fenster + 09:15-Test:      {n_clean_break}  ({n_clean_break/n_total_days:.1%})")
    print(f"3) ... mit verfügbarem Trend- UND Cross-Signal (kein Warmup):  {rows_with_signals}  ({rows_with_signals/n_total_days:.1%})")
    print(f"4a) ... die ALLE Continuation-Bedingungen erfüllen:            {n_continuation_candidates}")
    print(f"4b) ... die ALLE Reversal-Bedingungen erfüllen:                {n_reversal_candidates}")
    print(f"5a) Continuation-Kandidaten -> tatsächlicher Fraktal-Trigger:  {len(trades_continuation)} von {n_continuation_candidates}  "
          f"({len(trades_continuation)/n_continuation_candidates:.1%} finden vor Cutoff einen Trigger)")
    print(f"5b) Reversal-Kandidaten -> tatsächlicher Fraktal-Trigger:      {len(trades_reversal)} von {n_reversal_candidates}  "
          f"({len(trades_reversal)/n_reversal_candidates:.1%} finden vor Cutoff einen Trigger)")
    print(f"\nEndergebnis: {len(trades_both)} Trades von {n_total_days} Handelstagen ({len(trades_both)/n_total_days:.1%})")

    print("\n--- Filter-Trennschärfe (Anteil, der NACH Stufe 3 noch übrig ist) ---")
    print(f"grüne/rote (eindeutige) Rates-Tage: {(rates_ampel.isin(['grün','rot'])).mean():.1%} aller Tage (Rest: gelb)")
    print(f"Cross-confirmed=True-Anteil: {cross_confirm.mean():.1%}")
    print(f"Trend-Signal verfügbar ab: {trend.first_valid_index()}")


if __name__ == "__main__":
    main()
