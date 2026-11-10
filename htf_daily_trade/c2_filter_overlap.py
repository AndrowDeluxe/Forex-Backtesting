"""C2-Daily-Edge × Makro-Filter -- profitable Ueberschneidungen (Nutzerauftrag 10.11.2026).

    python -m htf_daily_trade.c2_filter_overlap                      # nur IS 2016-2021
    python -m htf_daily_trade.c2_filter_overlap --oeffnen --kombi F1+F2
                                     # friert C2 + Kombination ein, oeffnet OOS 2022-24 genau einmal
                                     # (nur nach Nutzerauswahl!)
    python -m htf_daily_trade.c2_filter_overlap --oeffnen --kombi F1+F3 --stufe blind
                                     # Blind 2010-15 genau einmal (2y-Zinsen ab 2009 noetig)

Basis: eingefrorenes C2 (htf_daily_trade.c2_goldfilter, Hash ff93efd9), unveraendert.
Filter je Trade (nur Daten vor dem Fuelltag):
  F1 Zins-Momentum   fusion_lab.filters.zins_fx (2y-Spread gegen USD, lag 20)
  F2 Carry           fusion_lab.filters.zins_fx (2y-Differenz; Metalle: Realzins faellt)
  F3 Regime-Matrix   Zinskurven-Regime 5 Tage bestaetigt, Richtung nach htf_daily_trade.macro
  F4 Regimekarte     Landi g×π, Linse "signs" (4 Regime); Richtung je Markt und Regime =
                     Vorzeichen der mittleren Tagesrendite des Markts im IS 2016-2021
Kombination = UND: ein Trade bleibt, wenn kein Filter der Kombination „dagegen“ ist.
Score k = mindestens k der 4 Filter „dafuer“.

Nutzervorgaben 10.11.: alle Kombinationen; Varianten nicht einzeln zaehlen, sondern nur die
finalen Faktoren; max. 10 Parameter je Variante; OOS 2022-24 gilt hier als nicht vorbelastet.
Auswahl trotzdem nur auf IS; OOS nur fuer die eine finale Kombination.
"""

from __future__ import annotations

import argparse
from itertools import combinations

import numpy as np
import pandas as pd

from fusion_lab.filters.zins_fx import ZinsFxFilter
from fusion_lab.filters.zinskurve_regime import confirmed, regime_series
from fusion_lab.macro_regime.model import daily_labels
from htf_daily_trade.backtest_r import MARKETS, load_market, stats
from htf_daily_trade.c2_goldfilter import CONFIG as BASE_CONFIG
from htf_daily_trade.c2_goldfilter import evaluate
from htf_daily_trade.macro import MARKET_KIND, REGIME_DIR
from research_lock import Lock, deflated_sharpe

FILTERS = ("F1", "F2", "F3", "F4")
NAMES = {"F1": "Zins-Momentum", "F2": "Carry", "F3": "Regime-Matrix", "F4": "Regimekarte g×π"}
PARAMS = {"zins_lag": 20, "regime_lag": 20, "regime_confirm": 5, "landi_linse": "signs"}
IS_START, IS_END = "2016-01-01", "2021-12-31"
MIN_N = 60
LOCK = "htf_daily_trade_c2_filter"


def _prev(s: pd.Series, date):
    i = s.index.searchsorted(pd.Timestamp(date), side="left") - 1
    return None if i < 0 else s.iloc[i]


def matrix_dir(regime: pd.Series, market: str, date) -> int:
    """F3: Matrix-Richtung des Markts (+1 long, −1 short, 0 keine Angabe)."""
    r = _prev(regime, date)
    if r is None or pd.isna(r):
        return 0
    kind, sgn = MARKET_KIND[market]
    pref = REGIME_DIR[r][kind]
    return 0 if pref is None else (1 if pref == "long" else -1) * sgn


def landi_dirs(labels: pd.DataFrame) -> dict:
    """F4: Richtung je (Markt, Regime) aus der IS-Tagesrendite -- nur 2016-2021."""
    out = {}
    for name in MARKETS:
        c = load_market(name)["Close"]
        ret = np.log(c).diff().loc[IS_START:IS_END]
        df = pd.DataFrame({"ret": ret}).join(labels[[PARAMS["landi_linse"]]], how="inner")
        for reg, m in df.groupby(PARAMS["landi_linse"])["ret"].mean().items():
            out[(name, reg)] = int(np.sign(m))
    return out


def label_trades(t: pd.DataFrame) -> pd.DataFrame:
    zf = ZinsFxFilter(PARAMS["zins_lag"])
    regime = confirmed(regime_series(PARAMS["regime_lag"]), PARAMS["regime_confirm"])
    days = pd.bdate_range("2009-01-01", pd.Timestamp.today())
    labels = daily_labels(days)
    ldir = landi_dirs(labels)
    lens = labels[PARAMS["landi_linse"]]
    rows = []
    for _, x in t.iterrows():
        d, m, side = pd.Timestamp(x["datum"]), x["markt"], x["seite"]
        reg = _prev(lens, d)
        dirs = {"F1": zf.momentum_dir(m, d), "F2": zf.carry_dir(m, d), "F3": matrix_dir(regime, m, d),
                "F4": ldir.get((m, reg), 0) if reg is not None else 0}
        rows.append({k: ZinsFxFilter.state(v, side) for k, v in dirs.items()})
    return pd.concat([t.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def keep(t: pd.DataFrame, kombi: tuple[str, ...]) -> pd.Series:
    return ~(t[list(kombi)] == "dagegen").any(axis=1)


def fmt(st: dict) -> str:
    if st.get("n", 0) < 2:
        return f"n {st.get('n', 0)}"
    return f"n {st['n']:>3}  Ø {st['mean_r']:+.3f} R  t {st['t']:+.2f}  PF {st['pf']:.2f}"


def single_effects(t: pd.DataFrame) -> list[str]:
    base = t["r"].mean()
    print(f"\n== Basis C2 (eingefroren): {fmt(stats(t['r']))}")
    print("\n== Einzelwirkung (wirkt = dafuer > Basis UND dagegen < Basis)")
    wirkt = []
    for f in FILTERS:
        mit, geg, neu = (t.loc[t[f] == s, "r"] for s in ("dafuer", "dagegen", "neutral"))
        ok = len(mit) > 1 and len(geg) > 1 and mit.mean() > base and geg.mean() < base
        wirkt += [f] if ok else []
        print(f"{f} {NAMES[f]:<16} dafuer: {fmt(stats(mit))} | dagegen: {fmt(stats(geg))} | "
              f"neutral n {len(neu)} | {'WIRKT' if ok else '-'}")
    return wirkt


def combo_table(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k in range(1, 5):
        for kombi in combinations(FILTERS, k):
            st = stats(t.loc[keep(t, kombi), "r"])
            rows.append({"variante": "+".join(kombi), **st})
    n_dafuer = (t[list(FILTERS)] == "dafuer").sum(axis=1)
    for k in range(1, 5):
        rows.append({"variante": f"Score>={k}", **stats(t.loc[n_dafuer >= k, "r"])})
    df = pd.DataFrame(rows)
    df["zu_duenn"] = df["n"] < MIN_N
    return df.sort_values(["zu_duenn", "t"], ascending=[True, False]).reset_index(drop=True)


def select(t: pd.DataFrame, variante: str) -> pd.Series:
    if variante.startswith("Score>="):
        return (t[list(FILTERS)] == "dafuer").sum(axis=1) >= int(variante[-1])
    return keep(t, tuple(variante.split("+")))


def breakdown(t: pd.DataFrame, variante: str) -> None:
    s = t.loc[select(t, variante)]
    print(f"\n-- {variante}")
    print(s.groupby("markt")["r"].agg(["size", "mean", "sum"]).round(2).T.to_string())
    print(s.groupby(pd.to_datetime(s["datum"]).dt.year)["r"].agg(["size", "mean", "sum"]).round(2).T.to_string())


def dsr(r: pd.Series, n_trials: int) -> float:
    return deflated_sharpe(r.mean() / r.std(ddof=1), len(r), n_trials)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oeffnen", action="store_true")
    ap.add_argument("--kombi", help="finale Kombination, z. B. F1+F2 oder Score>=2")
    ap.add_argument("--stufe", default="oos", choices=("oos", "blind"), help="je genau einmal")
    a = ap.parse_args()

    t = label_trades(evaluate(IS_START, IS_END, "2015-01-01"))
    t.to_csv("htf_daily_trade/c2_filter_overlap_is.csv", index=False)
    wirkt = single_effects(t)
    tab = combo_table(t)
    print(f"\n== Alle Kombinationen (IS, sortiert nach t; zu duenn = n < {MIN_N})")
    print(tab.round(3).to_string(index=False))
    for v in tab.loc[~tab["zu_duenn"], "variante"].head(3):
        breakdown(t, v)
    n_all = len(tab)
    print(f"\nEinzeln wirkende Faktoren: {', '.join(wirkt) or 'keine'}")
    if wirkt:
        r = t.loc[keep(t, tuple(wirkt)), "r"]
        print(f"Kombination der wirkenden Faktoren {'+'.join(wirkt)}: {fmt(stats(r))}")
        print(f"   DSR nach Nutzerregel (n = {len(wirkt)}): {dsr(r, len(wirkt)):.3f} | "
              f"zur Info mit allen {n_all} Varianten: {dsr(r, n_all):.3f}")

    if not a.oeffnen:
        return
    if not a.kombi:
        raise SystemExit("--kombi fehlt")
    n_factors = len([f for f in FILTERS if f in a.kombi]) if not a.kombi.startswith("Score") else 4
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, "2024-12-31")
    lock.register_blind("2010-01-01", "2015-12-31")
    if lock.trials == 0:
        lock.log_trials(n_factors, f"C2 + {a.kombi}; Nutzerregel 10.11.: nur finale Faktoren zaehlen "
                                   f"({n_all} Kombinationen im IS angesehen)")
    h = lock.freeze({**BASE_CONFIG, "makro_filter": a.kombi, "filter_params": PARAMS})
    warm = {"oos": "2021-01-01", "blind": "2009-01-01"}[a.stufe]
    start, end = lock.unseal(a.stufe, h)
    o = label_trades(evaluate(start, end, warm))
    o.to_csv(f"htf_daily_trade/c2_filter_overlap_{a.stufe}.csv", index=False)
    s = o.loc[select(o, a.kombi), "r"]
    print(f"\n== {a.stufe.upper()} {start}..{end} C2 + {a.kombi} (eingefroren {h[:8]}): {fmt(stats(s))}")
    print(f"   Basis C2 im selben Zeitraum: {fmt(stats(o['r']))}")
    breakdown(o, a.kombi)


if __name__ == "__main__":
    main()
