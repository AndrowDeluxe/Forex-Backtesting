"""Dennis (Elite Coaching, COT-Calls): Kandidat A' -- COT-Veraenderungsrate als Trendfilter.

    python -m scripts.research_dennis_cot_trend     # IS 2016-2021 + OOS 2022-2024 (OOS frei seit 10.11.)

Basis: Daily-Edge C2 mit Gold-Zinskurvenfilter (htf_daily_trade.c2_goldfilter.evaluate), unveraendert.
Filter je Trade, nur COT-Stand vor dem Fuelltag (Dienstag-Stichtag, Freitag veroeffentlicht = +3 Tage):
  NC   Netto-Position der Non-Commercials hat sich ueber die letzten N Berichte in Trade-Richtung
       veraendert (Dennis 5.3: "nur die Veraenderungsrate zaehlt"; Hedgefonds bauen auf).
  NR   zusaetzlich: Non-Reportables (Retail) in derselben Zeit NICHT in Trade-Richtung (Dennis 5.6:
       Hedgefonds gegen Retail).
  Richtung je Markt: Future = Basiswaehrung/Metall gegen USD; USDJPY invertiert (JPY-Future).
Varianten N in (2, 4, 8) x NR (aus, an) = 6, gezaehlt unter Sperre `dennis_cot_trend`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import stats
from htf_daily_trade.c2_goldfilter import evaluate
from research_lock import Lock, deflated_sharpe

LOCK = Lock("dennis_cot_trend")
COT = {"EURUSD": ("099741", 1), "GBPUSD": ("096742", 1), "AUDUSD": ("232741", 1),
       "USDJPY": ("097741", -1), "XAUUSD": ("088691", 1), "XAGUSD": ("084691", 1)}
VARIANTS = [(n, nr) for n in (2, 4, 8) for nr in (False, True)]


def cot_table() -> pd.DataFrame:
    d = pd.read_parquet("data_cache/smh/cot_legacy_nr.parquet")
    d["avail"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]) + pd.Timedelta(days=3)
    num = lambda c: pd.to_numeric(d[c])
    d["nc"] = num("noncomm_positions_long_all") - num("noncomm_positions_short_all")
    d["nr"] = num("nonrept_positions_long_all") - num("nonrept_positions_short_all")
    return d.drop_duplicates(["cftc_contract_market_code", "avail"]).sort_values("avail")


def deltas(cot: pd.DataFrame, code: str, day: pd.Timestamp, n: int) -> tuple[float, float] | None:
    s = cot[(cot["cftc_contract_market_code"] == code) & (cot["avail"] < day)]
    if len(s) <= n:
        return None
    return s["nc"].iloc[-1] - s["nc"].iloc[-1 - n], s["nr"].iloc[-1] - s["nr"].iloc[-1 - n]


def tag(trades: pd.DataFrame, cot: pd.DataFrame) -> pd.DataFrame:
    t = trades.copy()
    for n, nr in VARIANTS:
        keep = []
        for _, row in t.iterrows():
            code, inv = COT[row["markt"]]
            dd = deltas(cot, code, pd.Timestamp(row["datum"]), n)
            if dd is None:
                keep.append(False)
                continue
            want = (1 if row["seite"] == "long" else -1) * inv
            ok = np.sign(dd[0]) == want
            if nr:
                ok = ok and np.sign(dd[1]) != want
            keep.append(bool(ok))
        t[f"N{n}{'+NR' if nr else ''}"] = keep
    return t


def show(name: str, t: pd.DataFrame, n_trials: int) -> None:
    base = stats(t["r"])
    print(f"\n===== {name}: Basis C2  n {base['n']}, " + ", ".join(
        f"{k} {v:.3f}" for k, v in base.items() if k != "n"))
    rows = {}
    for n, nr in VARIANTS:
        col = f"N{n}{'+NR' if nr else ''}"
        kept, drop = t[t[col]]["r"], t[~t[col]]["r"]
        sr = kept.mean() / kept.std(ddof=1) if len(kept) > 2 else np.nan
        rows[col] = {"n_behalten": len(kept), "R_behalten": kept.mean(), "n_raus": len(drop),
                     "R_raus": drop.mean(), "Summe_R_behalten": kept.sum(),
                     "t": sr * np.sqrt(len(kept)) if len(kept) > 2 else np.nan,
                     "DSR": deflated_sharpe(sr, len(kept), n_trials) if len(kept) > 2 else np.nan}
    print(pd.DataFrame(rows).T.round(3).to_string())
    return pd.DataFrame(rows).T


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2024-12-31")
    cot = cot_table()
    n_trials = LOCK.log_trials(len(VARIANTS), "A' N x NR, Definitionen vorab im Docstring")
    t_is = tag(evaluate("2016-01-01", "2021-12-31", "2015-01-01"), cot)
    show("IS 2016-2021", t_is, n_trials).to_csv("scripts/research_dennis_cot_trend_is.csv")
    t_oos = tag(evaluate("2022-01-01", "2024-12-31", "2021-01-01"), cot)
    t_oos["datum"] = pd.to_datetime(t_oos["datum"])
    LOCK.oos_only(t_oos.set_index("datum"))  # protokolliert den OOS-Blick
    show("OOS 2022-2024", t_oos, n_trials).to_csv("scripts/research_dennis_cot_trend_oos.csv")


if __name__ == "__main__":
    main()
