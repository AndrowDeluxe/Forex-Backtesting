"""Blindtest 2010-2015 des eingefrorenen Daily-Kandidaten (Hash 6c55e525) -- Nutzerauftrag 11.11.2026.

    python -m htf_daily_trade.c2_blind --pruefen     # Code-Pruefung auf IS 2016-2017 gegen die eingefrorenen Trades
    python -m htf_daily_trade.c2_blind               # oeffnet Blind genau einmal (Lock htf_daily_filter_matrix)

Regeln unveraendert: C2 EL (wie filter_matrix.trades: alle C2-EL-Trades mit Ueberschneidungs-Sperre, danach Filter),
Faber 10M GEGEN (T6, Stand Vortag des Fuelltags), COT-Fluss MIT (4 Berichte, Fuelltag), Rohstoff-Veto 20 Tage
(AUDUSD~Kupfer, USDCAD~Oel), Stop Struktur, Ausstieg 10 Handelstage, kein BE. Kosten Spread+Kommission und
TTP-Swap-Modell. Leitzinsen gibt es erst ab 2015: davor ersetzt der 2J-Satz je Land den Leitzins (Naeherung).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from fusion_lab.filters.cot_flow import CotFlowFilter
from fusion_lab.macro_data import store
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.backtest_varianten import entries, simulate
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.c2_kandidat_report import add_swap, md, r_block, rates
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import LOCK, MARKETS, load_market, trend_dirs
from research_lock import Lock

FROZEN = "6c55e525f093389e1a1f61f862b350b8477909e96e64431719a83050c9543f4b"
VORLAUF = "2008-01-01"


def rates_mit_2y() -> pd.DataFrame:
    pol = rates()
    m = store.latest("macro")
    y2 = m[m["key"].str.endswith(".2y")].pivot_table(index="date", columns="key", values="value")
    y2.columns = [c.split(".")[0] for c in y2.columns]
    y2 = y2.sort_index().ffill() / 100.0
    early = y2.loc[y2.index < pol.index.min(), [c for c in pol.columns if c in y2.columns]]
    return pd.concat([early, pol]).sort_index().ffill().fillna(0.0)


def trades(start: str, end: str) -> pd.DataFrame:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    cot = CotFlowFilter(4)
    rows = []
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(VORLAUF):e], grid)
        td = trend_dirs(x)
        end_idx = int(np.searchsorted(x.index, e, side="right")) - 1
        busy = {"long": -1, "short": -1}
        for en in sorted((z for z in entries(x, "C") if z["v"] == "C2 EL"), key=lambda z: z["fill"]):
            t = x.index[en["fill"]]
            if t < s or en["fill"] > end_idx or en["fill"] <= busy[en["side"]]:
                continue
            res = simulate(x, en, "S1", "T8", cost, end_idx)
            if res is None:
                continue
            busy[en["side"]] = res["exit_k"]
            sign = 1 if en["side"] == "long" else -1
            rows.append({"markt": name, "seite": en["side"], "einstieg": t, "datum": t,
                         "ausstieg": x.index[res["exit_k"]], "kurs": en["price"], "stop": en["struct"],
                         "risiko_preis": sign * (en["price"] - en["struct"]), "kosten_preis": cost,
                         "r_netto_ohne_swap": res["r"], "r_brutto": res["r"] + cost / (sign * (en["price"] - en["struct"])),
                         "T6": td["T6"].iat[en["fill"] - 1] * sign, "M7": cot.direction(name, t) * sign})
    t = pd.DataFrame(rows)
    t = t[(t["T6"] < 0) & (t["M7"] > 0)].copy()
    t["RS"] = commodity_state(t, start="2007-06-01", end=(e + pd.Timedelta(days=40)).strftime("%Y-%m-%d"))
    t = t[t["RS"] != "gegen"].copy()
    t["periode"] = "blind"
    return add_swap(t, rates_mit_2y()).sort_values("einstieg").reset_index(drop=True)


def pruefen() -> None:
    ref = pd.read_csv("htf_daily_trade/c2_kandidat_trades.csv", parse_dates=["einstieg"])
    ref = ref[(ref["einstieg"] >= "2016-01-01") & (ref["einstieg"] <= "2017-12-31")]
    t = trades("2016-01-01", "2017-12-31")
    k = lambda d: set(zip(d["markt"], d["einstieg"].dt.normalize(), d["seite"]))
    a, b = k(t), k(ref)
    print(f"Pruefung IS 2016-17: neu {len(a)}, eingefroren {len(b)}, gemeinsam {len(a & b)}")
    m = t.merge(ref[["markt", "einstieg", "seite", "r_TTP"]], on=["markt", "einstieg", "seite"], suffixes=("", "_ref"))
    print(f"Ø R neu {m['r_TTP'].mean():+.3f} vs. eingefroren {m['r_TTP_ref'].mean():+.3f} (gemeinsame Trades)")


def main() -> None:
    if "--pruefen" in sys.argv:
        pruefen()
        return
    lock = Lock(LOCK)
    start, end = lock.unseal("blind", FROZEN)
    t = trades(start, end)
    t.to_csv("htf_daily_trade/c2_blind_trades.csv", index=False)
    rows = [{"Szenario": n, **r_block(t[c])} for n, c in (("ohne Swap", "r_netto_ohne_swap"),
                                                            ("Swap TTP", "r_TTP"), ("Stress", "r_stress"))]
    tab = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(f"== BLIND {start}..{end} (eingefroren {FROZEN[:8]}) ==")
    print(tab.round(3).to_string(index=False))
    lines = [f"# Blindtest {start}..{end} (eingefroren {FROZEN[:8]}, geoeffnet einmal)", "", md(tab, index=False), ""]
    for title, key in (("Je Jahr", t["einstieg"].dt.year), ("Je Markt", t["markt"]), ("Je Richtung", t["seite"])):
        g = t.groupby(key)["r_TTP"].agg(["size", "mean", "sum"]).rename(columns={"size": "n", "mean": "Ø R", "sum": "Σ R"})
        print(f"\n{title}\n{g.round(3).to_string()}")
        lines += [f"## {title} (Swap TTP)", "", md(g), ""]
    kt = t.rename(columns={"einstieg": "datum_e", "ausstieg": "exit_datum", "r_TTP": "r"})
    kt["datum"] = kt["datum_e"]
    for rk in (0.01, 0.02):
        k = konto(kt[["datum", "exit_datum", "r"]], lambda x, rk=rk: rk)
        line = f"Konto {rk:.0%}: Ende {k['ende']:,.0f}, CAGR {k['cagr']:+.1%}, max. DD {k['max_dd']:.1%}"
        print(line)
        lines.append(line)
    open("htf_daily_trade/c2_blind_report.md", "w", encoding="utf-8").write("\n".join(lines))


if __name__ == "__main__":
    main()
