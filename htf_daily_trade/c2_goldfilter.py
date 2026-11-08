"""Daily-Edge Typ C2 (Continuation, Limit-Einstieg) mit Gold-Zinskurven-Filter -- Kandidat zum Einfrieren.

    python -m htf_daily_trade.c2_goldfilter            # nur IS 2016-2021
    python -m htf_daily_trade.c2_goldfilter --oeffnen  # friert ein, oeffnet OOS 2022-24 und Blind 2010-15
                                                       # je genau einmal (nur nach Nutzerfreigabe!)

Konfiguration (vorab fest, Nutzerauftrag 02.11.2026):
  Signal C2: Schluss unter (ueber) den Dochten der 3 Vorkerzen, Manipulation in den 7 Tagen davor,
             Trend MA12/MA20; Einstieg Limit auf 50 % zwischen Ausloese-Schluss und Strukturstop,
             3 Tage gueltig; Stop S1 Struktur; Ausstieg T8 nach 10 Handelstagen.
  Maerkte:   EURUSD, GBPUSD, AUDUSD, USDJPY, XAUUSD, XAGUSD; XAUUSD nur in Richtung des
             GoldZinskurvenFilter (fusion_lab/filters/zinskurve_regime.py, lag 20, confirm 5).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter
from htf_daily_trade.backtest_r import MARKETS, features, load_market, stats
from htf_daily_trade.backtest_varianten import entries, simulate
from research_lock import Lock, deflated_sharpe

CONFIG = {"typ": "C2", "einstieg": "EL", "stop": "S1", "ziel": "T8", "rsi": None,
          "maerkte": sorted(MARKETS), "gold_filter": {"lag": 20, "confirm": 5}, "sweep_window": 7,
          "limit_tage": 3}


def evaluate(start: str, end: str, warmup_start: str) -> pd.DataFrame:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    flt = GoldZinskurvenFilter(**CONFIG["gold_filter"])
    rows = []
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(warmup_start):e], grid)
        end_idx = int(np.searchsorted(x.index, e, side="right")) - 1
        busy = {"long": -1, "short": -1}
        for en in sorted((z for z in entries(x, "C") if z["v"] == "C2 EL"), key=lambda z: z["fill"]):
            t = x.index[en["fill"]]
            if t < s or t > e or en["fill"] > end_idx or en["fill"] <= busy[en["side"]]:
                continue
            if name == "XAUUSD" and not flt.allows(en["side"], t):
                continue
            res = simulate(x, en, CONFIG["stop"], CONFIG["ziel"], cost, end_idx)
            if res is None:
                continue
            busy[en["side"]] = res["exit_k"]
            rows.append({"markt": name, "datum": t.date(), "seite": en["side"], "r": res["r"]})
    return pd.DataFrame(rows)


def show(title: str, t: pd.DataFrame, n_trials: int | None = None) -> None:
    st = stats(t["r"])
    line = ", ".join(f"{k} {v:.3f}" if isinstance(v, float) else f"{k} {v}" for k, v in st.items())
    print(f"\n== {title}: {line}")
    if n_trials:
        sr = t["r"].mean() / t["r"].std(ddof=1)
        print(f"   Deflated Sharpe ({n_trials} Versuche): {deflated_sharpe(sr, len(t), n_trials):.3f}")
    print(t.groupby("markt")["r"].agg(["size", "mean", "sum"]).round(2).T.to_string())
    print(t.groupby(pd.to_datetime(t["datum"]).dt.year)["r"].agg(["size", "mean", "sum"]).round(2).T.to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oeffnen", action="store_true")
    a = ap.parse_args()
    lock = Lock("htf_daily_trade_c")
    if lock.trials < 155:
        lock.log_trials(1, "C2 EL S1 T8 alle 6 Maerkte, Gold mit Zinskurven-Filter (Kandidat, 02.11.)")
    sp = lock.split
    t_is = evaluate(sp["is_start"], sp["is_end"], "2015-01-01")
    show("IS 2016-2021", t_is, lock.trials)
    t_is.to_csv("htf_daily_trade/c2_goldfilter_is.csv", index=False)
    if not a.oeffnen:
        return
    h = lock.freeze(CONFIG)
    for stage, warm in (("oos", "2021-01-01"), ("blind", "2009-01-01")):
        start, end = lock.unseal(stage, h)
        t = evaluate(start, end, warm)
        show(f"{stage.upper()} {start}..{end} (eingefroren {h[:8]})", t)
        t.to_csv(f"htf_daily_trade/c2_goldfilter_{stage}.csv", index=False)


if __name__ == "__main__":
    main()
