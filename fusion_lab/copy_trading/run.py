"""Gesamtlauf Stufe 1: Calls laden, Gueltigkeit, 20 Varianten, Ausgabe nach
fusion_lab/data/copy_trading/results/. Reaktionszeit 5 Min., Robustheitsprobe 60 Min.

    python -m fusion_lab.copy_trading.run
"""

import sys

import pandas as pd

from fusion_lab.copy_trading import data, sim
from fusion_lab.copy_trading.extract import CALLS, OUT_DIR

RES = OUT_DIR / "results"


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    calls, images = sim.load_calls(CALLS)
    end = pd.Timestamp(data.LAST_DAY, tz="UTC") + pd.Timedelta(days=1)
    calls = [c for c in calls if c.t_post < end]
    sim.assign_validity(calls, end)
    print(f"Bilder: {len(images) + len({c.msg_id for c in calls})}, davon Call-Setups gelesen: {len(calls)}")
    for lag_min in (5, 60):
        trades, audit = sim.simulate(calls, lag=pd.Timedelta(minutes=lag_min))
        trades.to_csv(RES / f"stufe1_trades_lag{lag_min}.csv", index=False)
        audit.to_csv(RES / f"stufe1_audit_lag{lag_min}.csv", index=False)
        summ = sim.summary(trades)
        summ.to_csv(RES / f"stufe1_summary_lag{lag_min}.csv", index=False)
        if lag_min == 5:
            print("\nVerworfene Setups:")
            print(audit["drop"].fillna("-> simuliert").value_counts().to_string())
        print(f"\n=== Stufe 1, Reaktionszeit {lag_min} Min. ===")
        print(summ.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    images.to_csv(RES / "bilder_ohne_call.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
