"""EUR/USD: "Stop Entry an der 6:00 Uhr Kerze" (User-Mentor-Idee,
2026-08-19) - statt auf einen Pullback-Fraktal ab 09:30 zu warten, sofort
zum fruehestmoeglichen lookahead-sicheren Zeitpunkt einsteigen (der bereits
per test_hour-Checkpoint-Fix gesicherte entry_start_i), SL = ATR-Floor statt
Fraktal-Pivot (siehe cls_practical/engine.py::simulate_cls_practical,
continuation_entry_mode="breakout_stop" - dortige Docstring fuer die exakte
Begruendung, warum NICHT am urspruenglichen 06:00-09:00-Break-Level selbst
gefuellt wird - das waere ein Lookahead-Risiko).

Betrifft NUR Continuation-Setups (Reversal unveraendert) - Vergleich daher
auf allowed_setups=("continuation",) beschraenkt fuer einen sauberen
Ceteris-paribus-Vergleich, plus einmal auf dem vollen Sample (Conti+Rev)
zur Einordnung des Gesamteffekts."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in cls_advanced.PAIRS if p != "EURUSD"]
TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0


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
    print(f"    {label:32s}: n={row['n']:>3d} WR={row['win_rate']:5.1f}% avg_R={row['avg_r']:+.3f} PF={row['profit_factor']:.2f} "
          f"PnL=${row['total_pnl']:+,.0f} Sharpe={row['sharpe']:.2f} MaxDD={row['max_drawdown_pct']:.2f}% | "
          f"IS(n={row['n_is']:>3d}) avg_R={row['avg_r_is']:+.3f} | OOS(n={row['n_oos']:>3d}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    rows = []
    print("\n" + "=" * 100 + "\nNUR CONTINUATION (Ceteris-paribus-Vergleich)\n" + "=" * 100)
    t_fractal_cont = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, allowed_setups=("continuation",))
    rows.append({**stats(t_fractal_cont, "Fraktal (Baseline)"), "group": "continuation_only"})
    t_stop_cont = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, allowed_setups=("continuation",),
                                          continuation_entry_mode="breakout_stop")
    rows.append({**stats(t_stop_cont, "Breakout-Stop (neu)"), "group": "continuation_only"})

    print("\n" + "=" * 100 + "\nVOLLES SAMPLE (Continuation+Reversal, Reversal unveraendert)\n" + "=" * 100)
    t_fractal_full = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    rows.append({**stats(t_fractal_full, "Fraktal (Baseline)"), "group": "full"})
    t_stop_full = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, continuation_entry_mode="breakout_stop")
    rows.append({**stats(t_stop_full, "Breakout-Stop (neu)"), "group": "full"})

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_breakout_stop_entry_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
