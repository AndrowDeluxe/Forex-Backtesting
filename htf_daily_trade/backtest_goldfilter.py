"""Gold-Zinskurven-Filter auf den Daily-Edge (nur XAUUSD, IS 2016-2021) -- Nutzerauftrag 02.11.2026.

    python -m htf_daily_trade.backtest_goldfilter

Vorab festgelegte Kandidaten (je zwei beste aus dem Varianten-Raster):
  Typ C: C2 EL S1 T8, C2 EL S3 T8      Typ R: E3 S1 T7, E2 S1 T6
Je Kandidat: ohne Filter (bereits gezaehlt) / mit Filter (gezaehlt, +2 je Lock) /
gegen Filter (Kontrolle). Filter: fusion_lab.filters.zinskurve_regime.GoldZinskurvenFilter
(Regime 20 Tage, 5 Tage bestaetigt; Goldilocks/Reflation long, Inflation short, Deflation beide).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter
from htf_daily_trade.backtest_r import MARKETS, features, load_market, stats
from htf_daily_trade.backtest_varianten import entries, simulate
from research_lock import Lock, deflated_sharpe

CANDIDATES = [("C", "C2 EL", "S1", "T8"), ("C", "C2 EL", "S3", "T8"),
              ("R", "E3", "S1", "T7"), ("R", "E2", "S1", "T6")]


def run(x, ens, cost, ent, stop, tgt, mode, flt, is_start, is_end):
    end_idx = int(np.searchsorted(x.index, is_end, side="right")) - 1
    busy, rows = {"long": -1, "short": -1}, []
    for en in sorted((e for e in ens if e["v"] == ent), key=lambda e: e["fill"]):
        t = x.index[en["fill"]]
        if t < is_start or t > is_end or en["fill"] > end_idx or en["fill"] <= busy[en["side"]]:
            continue
        ok = flt.allows(en["side"], t)
        if (mode == "mit" and not ok) or (mode == "gegen" and (ok and flt.direction(t) != 0)):
            continue
        if mode == "gegen" and flt.direction(t) == 0:
            continue  # Kontrolle: nur Trades, die der Filter ausdruecklich verbietet
        res = simulate(x, en, stop, tgt, cost, end_idx)
        if res is None:
            continue
        busy[en["side"]] = res["exit_k"]
        rows.append({"datum": t.date(), "seite": en["side"], "r": res["r"], "regime": flt.regime_at(t)})
    return pd.DataFrame(rows)


def main() -> None:
    locks = {"R": Lock("htf_daily_trade_r"), "C": Lock("htf_daily_trade_c")}
    for k, lk in locks.items():
        if lk.trials < 152 + 2:
            lk.log_trials(2, "Gold-Zinskurven-Filter (5T bestaetigt) auf 2 vorab gewaehlte Kandidaten, nur Gold (02.11.)")
    is_start, is_end = pd.Timestamp("2016-01-01"), pd.Timestamp("2021-12-31")
    _, grid, cost = MARKETS["XAUUSD"]
    x = features(load_market("XAUUSD").loc[pd.Timestamp("2015-01-01"):is_end], grid)
    ens = {"R": entries(x, "R"), "C": entries(x, "C")}
    flt = GoldZinskurvenFilter()
    pd.set_option("display.width", 160)
    rows = []
    for typ, ent, stop, tgt in CANDIDATES:
        for mode in ("ohne", "mit", "gegen"):
            t = run(x, ens[typ], cost, ent, stop, tgt, mode, flt, is_start, is_end)
            st = stats(t["r"]) if len(t) > 1 else {"n": len(t)}
            row = {"kandidat": f"{typ} {ent} {stop} {tgt}", "filter": mode, **st}
            if mode == "mit" and len(t) > 1:
                sr = t["r"].mean() / t["r"].std(ddof=1)
                row["dsr"] = deflated_sharpe(sr, len(t), locks[typ].trials)
                row["long/short"] = f"{(t.seite == 'long').sum()}/{(t.seite == 'short').sum()}"
                row["jahre_pos"] = int((t.groupby(pd.to_datetime(t.datum).dt.year).r.mean() > 0).sum())
            rows.append(row)
    res = pd.DataFrame(rows)
    print(res.round(3).to_string(index=False))
    res.to_csv("htf_daily_trade/goldfilter_is.csv", index=False)


if __name__ == "__main__":
    main()
