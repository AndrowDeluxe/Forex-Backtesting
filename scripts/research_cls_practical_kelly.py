"""Kelly-Formel auf cls_practical (User-Anfrage 2026-08-13), exakt dieselbe
Methodik wie scripts/research_kelly_ou_model.py fuers OU-Modell: f* = p -
q/b, wobei b = Ø Gewinn-R / |Ø Verlust-R|, aus den bereits vorhandenen
R-Multiples (pnl_usd/risk_amount_usd) berechnet. In-Sample UND
Out-of-Sample getrennt (derselbe SPLIT wie ueberall in diesem Track), um
zu pruefen, ob sich die implizite Kelly-Groesse zwischen den Fenstern
stabil verhaelt oder wie beim OU-Modell/London-Range typische Ueberraschungen
zeigt."""

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
CURRENT_RISK_PCT = 0.01  # User-Vorgabe: Risk Management vorerst auf 1% (nicht engine.py's Default 0.5%)


def kelly_stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"{label}: keine Trades")
        return {}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins, losses = r[r > 0], r[r <= 0]
    p = len(wins) / n
    q = 1 - p
    avg_win = wins.mean() if len(wins) else np.nan
    avg_loss = losses.mean() if len(losses) else np.nan
    b = avg_win / abs(avg_loss) if len(losses) and avg_loss != 0 else np.nan
    kelly_f = p - q / b if pd.notna(b) and b != 0 else np.nan
    row = {
        "label": label, "n_trades": n, "win_rate": p, "avg_win_r": avg_win, "avg_loss_r": avg_loss,
        "payoff_ratio_b": b, "kelly_f": kelly_f, "half_kelly_f": kelly_f / 2 if pd.notna(kelly_f) else np.nan,
        "quarter_kelly_f": kelly_f / 4 if pd.notna(kelly_f) else np.nan, "used_risk_pct": CURRENT_RISK_PCT,
    }
    print(f"{label}: n={n} WR={p*100:.1f}% avg_win={avg_win:+.2f}R avg_loss={avg_loss:+.2f}R "
          f"b={b:.2f} Kelly f*={kelly_f*100:.2f}% Half-Kelly={row['half_kelly_f']*100:.2f}% "
          f"Quarter-Kelly={row['quarter_kelly_f']*100:.2f}% (genutzt: {CURRENT_RISK_PCT*100:.1f}%)")
    return row


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)

    rows = []
    rows.append(kelly_stats(trades, "Gesamt (2018-2026)"))
    rows.append(kelly_stats(trades[trades["entry_time"] < SPLIT], "In-Sample (2018-12/2022-06)"))
    rows.append(kelly_stats(trades[trades["entry_time"] >= SPLIT], "Out-of-Sample (2022-06/2026-08)"))
    rows.append(kelly_stats(trades[trades["setup"] == "continuation"], "  davon Continuation"))
    rows.append(kelly_stats(trades[trades["setup"] == "reversal"], "  davon Reversal"))

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "kelly.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
