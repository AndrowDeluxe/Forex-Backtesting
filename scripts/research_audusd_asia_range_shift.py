"""AUD/USD mit allen validierten EUR/USD-Bausteinen, aber Asia-Range
04:00-08:00 statt der Standard-Zeit 00:00-06:00 (User-Anfrage 2026-08-20).

"Alle Ansaetze aus EUR/USD" = der aktuell LIVE-validierte Stack: 09:00-
Haltetest-Checkpoint, Trend-Filter (SMA100+ADX>=15), Cross-Filter (die
ORIGINALE compute_cross_confirmation ueber die anderen 5 Majors, per
_USD_IS_QUOTE-Monkeypatch fuer AUD/USD korrekt, siehe
scripts/research_cls_practical_g8_majors_point0900.py), Rates-Filter als
GATE aus (Standard-Default). NICHT dabei: die Zins-Risiko-Skalierung (
compute_daily_rate_risk_multiplier braucht BUND vs. USTBOND - fuer AUD/USD
gibt es aber keine passende AUD-Seite auf Dukascopy, nur BUND/UKGILT/
USTBOND existieren als Anleihe-CFDs, siehe Memory cls-practical-strategy-
state) - waere kein fairer Baustein-Uebertrag, deshalb bewusst
ausgelassen und hier offengelegt statt stillschweigend mit der falschen
Waehrung (BUND) simuliert.

Asia-Range-Interpretation (siehe cls_practical/engine.py's
asia_start/asia_end-Docstring): NUR die Asia-Range-Definition wird
geaendert (4:00-8:00 statt 0:00-6:00), Settle-Fenster bleibt
[asia_end, SETTLE_END) = 08:00-09:00 (statt 06:00-09:00), Checkpoint/Entry-
Fenster bleiben unveraendert bei 09:00/09:30-12:00 - eine bewusste
Minimal-Aenderung (nur EIN Parameter isoliert), keine Verschiebung des
gesamten Tagesablaufs."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from combined_strategy.data import INSTRUMENTS, OFFER_SIDE

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
PRIMARY = "AUDUSD"
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0


def fetch_m5_berlin_generic(key: str, start: str, end: str) -> pd.DataFrame:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = dukascopy_python.fetch(
        INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def daily_pnl_series(trades: pd.DataFrame, start: str, end: str) -> pd.Series:
    full_days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    if len(trades) == 0:
        return pd.Series(0.0, index=full_days)
    exit_day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    return trades.groupby(exit_day)["pnl_usd"].sum().reindex(full_days, fill_value=0.0)


def equity_metrics(daily_pnl: pd.Series) -> dict:
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    daily_ret = equity.pct_change().fillna(0.0)
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    max_dd = dd.min()
    years = len(daily_pnl) / TRADING_DAYS_PER_YEAR
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else float("nan")
    sharpe = (daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_ret.std(ddof=1) > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd not in (0, float("nan")) else float("nan")
    return {"sharpe": sharpe, "calmar": calmar, "max_drawdown_pct": max_dd * 100}


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"    {label}: keine Trades")
        return {"label": label, "n": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    m = equity_metrics(daily_pnl_series(trades, START, END))
    row = {
        "label": label, "n": n, "win_rate": win_rate * 100, "avg_r": r.mean(), "profit_factor": pf,
        "total_pnl": trades["pnl_usd"].sum(), "n_is": int(is_mask.sum()),
        "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
        **m,
    }
    print(f"    {label:28s}: n={row['n']:>3d} WR={row['win_rate']:5.1f}% avg_R={row['avg_r']:+.3f} PF={row['profit_factor']:.2f} "
          f"PnL=${row['total_pnl']:+,.0f} Sharpe={row['sharpe']:.2f} MaxDD={row['max_drawdown_pct']:.2f}% | "
          f"IS(n={row['n_is']:>3d}) avg_R={row['avg_r_is']:+.3f} | OOS(n={row['n_oos']:>3d}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Daten (AUD/USD M5 + 5 Majors M15 + Rates)...")
    audusd_m5 = fetch_m5_berlin_generic(PRIMARY, START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in cls_advanced.PAIRS if p != PRIMARY}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    cls_advanced._USD_IS_QUOTE["EURUSD"] = cls_advanced._USD_IS_QUOTE[PRIMARY]
    try:
        rows = []
        print("\n" + "=" * 100 + "\nAUD/USD, Standard-Asia-Range 00:00-06:00 (Referenz)\n" + "=" * 100)
        t_std = simulate_cls_practical(audusd_m5, other_majors_m15, bund_m5, ustbond_m5)
        rows.append({**stats(t_std, "Standard 00:00-06:00"), "asia_range": "00-06"})

        print("\n" + "=" * 100 + "\nAUD/USD, Asia-Range 04:00-08:00 (neu)\n" + "=" * 100)
        t_shift = simulate_cls_practical(audusd_m5, other_majors_m15, bund_m5, ustbond_m5, asia_start=4.0, asia_end=8.0)
        rows.append({**stats(t_shift, "Verschoben 04:00-08:00"), "asia_range": "04-08"})
    finally:
        cls_advanced._USD_IS_QUOTE["EURUSD"] = True

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "audusd_asia_range_shift.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
