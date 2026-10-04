"""ORB: Monte Carlo der Kandidaten aus dem M1-Exit-Gitter (tick-korrigiert).

Folgt auf scripts/research_orb_exit_grid_m1.py (Nutzerauftrag 2026-10-03,
"teste beide Punkte nochmal durch"). Ein Gitter mit 112 Kombinationen je
Instrument findet immer irgendwo ein Optimum -- hier muessen die Kandidaten
im Portfolio, im Monte Carlo und Jahr fuer Jahr halten.

Je Bein die Trade-Reihe in R (gleiches Risiko je Trade), tick-korrigiert:
Fuell-Minute mit SL-Touch NACH der Fuellung -> sofortiger Stop-out; bei der
Storno-am-SL-Regel faellt ein Trade mit SL-Touch VOR der Fuellung weg.
Portfolio = Summe der Beine je Monat. Block-Bootstrap ueber Kalendermonate,
3.000 Pfade (wie research_orb_exit_montecarlo.py).
Ausgabe: ny_open_orb/results/m1_candidates_montecarlo.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_orb_cancel_at_sl_and_hold import END, START, find_live_entries  # noqa: E402
from research_orb_cancel_at_sl_montecarlo import load_m1  # noqa: E402
from research_orb_exit_grid_m1 import RES, prepare, sim  # noqa: E402

N_PATHS = 3000
RNG = np.random.default_rng(20261004)

# (Regel, Stop, Ziel, Teilziel)
LEGS = {
    "SP500 heute": ("SP500", "opposite", 0.6, 6.0, None),
    "US30 heute": ("US30", "opposite", 0.6, 6.0, 3.0),
    "NASDAQ heute": ("NASDAQ", "none", 0.6, None, 3.0),
    "NASDAQ ohne Teilziel": ("NASDAQ", "none", 0.6, None, None),
    "NASDAQ Storno+ohne Teilziel": ("NASDAQ", "sl", 0.6, None, None),
    "NASDAQ Storno+Teilziel 3R": ("NASDAQ", "sl", 0.6, None, 3.0),
}
PORTFOLIOS = {
    "A heute (Variante C)": ["SP500 heute", "US30 heute", "NASDAQ heute"],
    "B NASDAQ ohne Teilziel": ["SP500 heute", "US30 heute", "NASDAQ ohne Teilziel"],
    "C NASDAQ Storno+ohne Teilziel": ["SP500 heute", "US30 heute", "NASDAQ Storno+ohne Teilziel"],
    "D = B ohne US30": ["SP500 heute", "NASDAQ ohne Teilziel"],
    "E = C ohne US30": ["SP500 heute", "NASDAQ Storno+ohne Teilziel"],
}


def leg_series(frames, ticks, instrument, rule, stop, target, partial) -> pd.Series:
    frame, allowed = frames[instrument]
    prep = prepare(frame, find_live_entries(frame, allowed, stop, rule))
    res = sim(prep, instrument, stop, target, partial)
    keys = [f"{instrument}|{t}" for t in res["entry_time"]]
    before = np.array([bool(ticks.at[k, f"sl_before_{stop}"]) if k in ticks.index else False for k in keys])
    after = np.array([bool(ticks.at[k, f"sl_after_{stop}"]) if k in ticks.index else False for k in keys])
    r = np.where(after, res["stop_out_r"], res["r"])
    keep = ~(before & (rule == "sl"))
    idx = pd.to_datetime(res["entry_time"]).dt.tz_convert(None)
    return pd.Series(r[keep], index=idx[keep]).sort_index()


def mc(monthly: pd.Series):
    vals = monthly.to_numpy()
    idx = RNG.integers(0, len(vals), size=(N_PATHS, len(vals)))
    # Monatsbloecke: innerhalb eines Monats ist die Reihenfolge fuer den DD
    # zweitrangig -- gezogen werden ganze Monatssummen, wie im Bestandsskript.
    paths = np.cumsum(vals[idx], axis=1)
    total = paths[:, -1]
    peak = np.maximum.accumulate(np.concatenate([np.zeros((N_PATHS, 1)), paths], axis=1), axis=1)[:, 1:]
    maxdd = (paths - peak).min(axis=1)
    return total, maxdd


def main() -> int:
    ticks = pd.read_csv(RES / "fill_minute_ticks.csv")
    ticks.index = ticks["instrument"] + "|" + ticks["entry_time"].astype(str)
    frames = {i: load_m1(i) for i in ("SP500", "US30", "NASDAQ")}
    months = pd.period_range(pd.Timestamp(START), pd.Timestamp(END), freq="M")

    series = {name: leg_series(frames, ticks, *spec) for name, spec in LEGS.items()}

    print("Jahresreihe je Bein (Σ R, tick-korrigiert):")
    yearly = pd.DataFrame({n: s.groupby(s.index.year).sum() for n, s in series.items()}).round(1)
    print(yearly.to_string())
    print("\nTrades je Bein:", {n: len(s) for n, s in series.items()})

    rows = []
    print(f"\nPortfolio-Monte-Carlo ({N_PATHS} Pfade, Block = Kalendermonat, 1 R je Trade und Bein):")
    for pname, legs in PORTFOLIOS.items():
        monthly = sum(series[l].groupby(series[l].index.to_period("M")).sum().reindex(months, fill_value=0.0)
                      for l in legs)
        total, maxdd = mc(monthly)
        ratio = total / np.abs(np.minimum(maxdd, -1e-9))
        hist_eq = monthly.cumsum()
        oos = monthly[monthly.index >= pd.Period("2023-01", "M")]
        row = {"portfolio": pname, "sum_hist": monthly.sum(), "oos_sum": oos.sum(),
               "maxdd_hist": (hist_eq - hist_eq.cummax()).min(),
               "neg_months": (monthly < 0).mean(), "sum_med": np.median(total), "sum_p5": np.percentile(total, 5),
               "dd_med": np.median(maxdd), "dd_p95": np.percentile(maxdd, 5),
               "ratio_med": np.median(ratio), "ratio_p5": np.percentile(ratio, 5), "p_neg": (total < 0).mean()}
        rows.append(row)
        print(f"  {pname:<32} Σ R hist {row['sum_hist']:+6.0f} (OOS {row['oos_sum']:+5.0f}) | "
              f"MaxDD hist {row['maxdd_hist']:6.1f} | MC: Σ Median {row['sum_med']:+6.0f} (P5 {row['sum_p5']:+5.0f}) | "
              f"MaxDD Median {row['dd_med']:6.1f} / P95 {row['dd_p95']:6.1f} | Ertrag/DD Median {row['ratio_med']:.2f} "
              f"(P5 {row['ratio_p5']:.2f}) | P(Σ<0) {row['p_neg']:.1%}")
    pd.DataFrame(rows).to_csv(RES / "m1_candidates_montecarlo.csv", index=False)

    # US30 allein: traegt das Bein ueberhaupt?
    s = series["US30 heute"]
    monthly = s.groupby(s.index.to_period("M")).sum().reindex(months, fill_value=0.0)
    total, _ = mc(monthly)
    oos = s[s.index >= "2023-01-01"]
    print(f"\nUS30 heute allein: Σ R {s.sum():+.0f}, OOS {oos.sum():+.1f} R aus {len(oos)} Trades "
          f"(Ø {oos.mean():+.3f}), MC P(Σ<0) {(total < 0).mean():.1%}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
