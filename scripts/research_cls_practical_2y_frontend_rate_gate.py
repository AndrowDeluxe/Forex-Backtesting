"""Front-End-2Y-Zinsfilter als TRADE-GATE/Confirmation statt Risiko-Skalierung
(User-Anfrage 2026-08-21: "teste das ganze auf EU als zusaetzliche
confirmation ... dieser Filter sollte ja urspruenglich mal die Validierung
[...] machen"). Exakt dieselbe Rolle, die der Long-End-Proxy ZUERST bekam,
bevor sich Risiko-Skalierung als staerker erwies (siehe
scripts/research_cls_practical_daily_rate_filter.py, User-Zitat dort:
"die Richtung der letzten Tageskerze als Validierung fuer unseren Trade") -
und dieselbe Rolle, die "Rates-Bestaetigung" in der Quelle (strategy/
cls_advanced.py Check 1) urspruenglich im Entscheidungsbaum hatte: ein
Gate/Confirmation-Check, kein reiner Sizing-Overlay.

use_rates_filter=True + rates_score_override=<2Y-Score> nutzt exakt denselben
Mechanismus in simulate_cls_practical(), den die Long-End-Version schon
hatte - kein Engine-Change noetig. Gleiche Sweep-Methodik wie das Long-End-
Original: lag_days x z_threshold x filter_mode (and/majority), avg_R/WinRate/
PF, IS(2018-12-01..2022-06-01)/OOS(2022-06-01..2026-08-11), "beide besser"-
Zusammenfassung."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin, fetch_2y_yield_daily
from cls_practical.engine import simulate_cls_practical
from cls_practical.rates import compute_daily_rate_score_2y

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
OTHER_MAJORS = [p for p in cls_advanced.PAIRS if p != "EURUSD"]


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        return {"label": label, "n": 0, "avg_r": float("nan"), "n_is": 0, "avg_r_is": float("nan"), "n_oos": 0, "avg_r_oos": float("nan")}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    row = {
        "label": label, "n": n, "win_rate": win_rate * 100, "avg_r": r.mean(), "profit_factor": pf,
        "total_pnl": trades["pnl_usd"].sum(), "n_is": int(is_mask.sum()),
        "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }
    print(f"  {label:38s}: n={row['n']:>3d} WR={row['win_rate']:5.1f}% avg_R={row['avg_r']:+.3f} PF={row['profit_factor']:.2f} "
          f"PnL=${row['total_pnl']:+,.0f} | IS(n={row['n_is']:>3d}) avg_R={row['avg_r_is']:+.3f} | "
          f"OOS(n={row['n_oos']:>3d}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 + BUND/USTBOND M5 + TVC DE02Y/US02Y)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    de02y = fetch_2y_yield_daily("DE02Y")
    us02y = fetch_2y_yield_daily("US02Y")

    print("\n" + "=" * 100 + "\nBASELINE (kein Zinsfilter)\n" + "=" * 100)
    baseline_trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, use_rates_filter=False)
    baseline = stats(baseline_trades, "Baseline (use_rates_filter=False)")

    rows = [baseline]
    print("\n" + "=" * 100 + "\nFRONT-END 2Y ALS GATE: lag_days x z_threshold x filter_mode\n" + "=" * 100)
    for lag_days in (1, 2, 3):
        score = compute_daily_rate_score_2y(de02y, us02y, lag_days=lag_days)
        for z_threshold in (0.0, 0.25, 0.5):
            for filter_mode in ("and", "majority"):
                label = f"2Y lag={lag_days}d z>={z_threshold} mode={filter_mode}"
                trades = simulate_cls_practical(
                    eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                    use_rates_filter=True, rates_score_override=score,
                    rates_z_threshold=z_threshold, filter_mode=filter_mode,
                )
                row = stats(trades, label)
                row.update({"lag_days": lag_days, "z_threshold": z_threshold, "filter_mode": filter_mode})
                rows.append(row)

    df = pd.DataFrame(rows)
    variant_rows = df[df["label"] != baseline["label"]]
    both_beat = variant_rows[
        (variant_rows["avg_r_is"] > baseline["avg_r_is"]) & (variant_rows["avg_r_oos"] > baseline["avg_r_oos"])
    ]
    print(f"\nBaseline: IS avg_R={baseline['avg_r_is']:+.3f} (n={baseline['n_is']}) -> OOS avg_R={baseline['avg_r_oos']:+.3f} (n={baseline['n_oos']})")
    print(f"\nVarianten, die die Baseline auf IS UND OOS GLEICHZEITIG schlagen ({len(both_beat)}):")
    if len(both_beat) == 0:
        print("  keine")
    else:
        for _, r in both_beat.sort_values("avg_r_is", ascending=False).iterrows():
            print(f"  {r['label']:38s}: IS avg_R={r['avg_r_is']:+.3f} (n={r['n_is']:.0f}) -> "
                  f"OOS avg_R={r['avg_r_oos']:+.3f} (n={r['n_oos']:.0f})")

    if len(variant_rows.dropna(subset=["avg_r_is"])) > 0:
        winner = variant_rows.loc[variant_rows["avg_r_is"].idxmax()]
        print(f"\nIS-Gewinner: {winner['label']} (IS avg_R={winner['avg_r_is']:+.3f}) -> "
              f"OOS avg_R={winner['avg_r_oos']:+.3f} (n_oos={winner['n_oos']:.0f})")

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "2y_frontend_rate_gate_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
