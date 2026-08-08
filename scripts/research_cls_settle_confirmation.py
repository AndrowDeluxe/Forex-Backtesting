"""Variante 2/3 der CLS-Settle-Idee (2026-08-05): statt eines eigenen
CLS-Settle-Trades (siehe research_cls_settle_breakout.py, klar negativ) -
(a) den bereits validierten Asia-Range-Trade NUR nehmen, wenn er vor/
zeitgleich mit seinem Entry durch einen CLS-Settle-Teilrange-Ausbruch in
dieselbe Richtung bestätigt wurde, und (b) beide Systeme unabhängig
kombiniert (gepoolt) betrachten."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.cls_settle import check_settle_confirmation, fetch_gold_m15_berlin, simulate_cls_settle_breakout
from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import apply_adx_filter

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"


def _pf_wr(trades):
    if trades.empty:
        return float("nan"), float("nan"), 0
    wins = trades["return_pct"] > 0
    gross_win = trades.loc[wins, "return_pct"].sum()
    gross_loss = -trades.loc[~wins, "return_pct"].sum()
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    return pf, wins.mean(), len(trades)


def report(label, trades):
    split_ts = pd.Timestamp(SPLIT, tz=trades["entry_time"].dt.tz)
    is_t = trades[trades["entry_time"] < split_ts]
    oos_t = trades[trades["entry_time"] >= split_ts]
    pf_full, wr_full, n_full = _pf_wr(trades)
    pf_is, _, _ = _pf_wr(is_t)
    pf_oos, _, _ = _pf_wr(oos_t)
    print(f"{label:38s} n={n_full:4d} PF_full={pf_full:.3f} PF_IS={pf_is:.3f} PF_OOS={pf_oos:.3f} win_rate={wr_full:.1%}")


def main():
    print("Lade Daten...")
    df_ny = fetch_gold_m15(START, END)
    df_berlin = fetch_gold_m15_berlin(START, END)

    asia_trades = simulate_asian_breakout(df_ny, stop_frac=1.0)
    asia_trades = apply_adx_filter(asia_trades, adx_min=15)
    print(f"\nBasis: {len(asia_trades)} Asia-Trades (ADX-gefiltert, validierte Standard-Config)")
    report("Alle Asia-Trades (Baseline)", asia_trades)

    print("\n=== Variante 2: nur Settle-bestätigte Asia-Trades ===")
    confirmed_mask = check_settle_confirmation(df_berlin, asia_trades)
    print(f"Bestätigt: {confirmed_mask.sum()} von {len(asia_trades)} ({confirmed_mask.mean():.1%})")
    confirmed_trades = asia_trades[confirmed_mask]
    unconfirmed_trades = asia_trades[~confirmed_mask]
    report("NUR bestätigte Asia-Trades", confirmed_trades)
    report("NUR unbestätigte Asia-Trades (Kontrolle)", unconfirmed_trades)

    print("\n=== Variante 3: Asia + CLS-Settle kombiniert (gepoolt) ===")
    settle_trades = simulate_cls_settle_breakout(df_berlin)
    print(f"CLS-Settle-Trades: {len(settle_trades)}")
    report("CLS-Settle allein (Referenz)", settle_trades)

    def _utc(df):
        out = df[["entry_time", "return_pct"]].copy()
        out["entry_time"] = out["entry_time"].dt.tz_convert("UTC")
        return out

    combined = pd.concat(
        [_utc(asia_trades).assign(system="asia"), _utc(settle_trades).assign(system="settle")],
        ignore_index=True,
    ).sort_values("entry_time")
    report("Asia + Settle gepoolt (alle)", combined)

    combined_confirmed_only = pd.concat(
        [_utc(confirmed_trades).assign(system="asia_confirmed"), _utc(settle_trades).assign(system="settle")],
        ignore_index=True,
    ).sort_values("entry_time")
    report("Nur bestätigte Asia + Settle gepoolt", combined_confirmed_only)


if __name__ == "__main__":
    main()
