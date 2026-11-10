"""Bester C2-Kandidat × Stop / Ziel / Breakeven / Teilgewinne / Risiko-Staffel (Nutzerauftrag 11.11.2026).

    python -m htf_daily_trade.c2_exit_varianten

Kandidat (noch nicht eingefroren): C2 EL + Faber gegen (T6) + COT-Fluss mit (M7) + Rohstoff-Veto (B6),
9 Maerkte, IS 2016-2021 / OOS 2022-2024. Einstiege bleiben fest (die Trade-Liste der Basis-Simulation);
nur das Management danach aendert sich, Ueberschneidungen werden nicht neu aufgeloest.

Stop      S1 Struktur (Basis) | S2 2x ATR | S3 1x ATR | S4 Extrem der Vortageskerze
Ausstieg  A0 alles nach 10 Tagen (Basis T8) | A1 alles 2 R | A2 alles 3 R | A3 alles externe Liquiditaet
          (20-Tage-Hoch/-Tief vor dem Einstieg, sonst 3 R) | A4 alles Trail (Schluss unter Vortagestief)
          A5 Twin 1/2 2 R + 1/2 10 Tage | A6 Twin 1/2 3 R + 1/2 Trail | A7 Twin 1/2 2 R + 1/2 Liquiditaet
          A8 Teilgewinne 1/3 bei 1 R, 1/3 bei 2 R, Rest 10 Tage | A9 1/2 bei 1 R, Rest 10 Tage
Breakeven B0 keiner | B1 ab 1 R | B2 ab 1,5 R (Stop der Restposition auf Einstieg ab der Folgekerze)
Halten: Zeitbeine 10 Tage, Ziel-Beine max. 15, Trail max. 30. Trifft eine Kerze Stop und Ziel, zaehlt der Stop.
Kosten einmal je Trade (Spread + Kommission). Alle Varianten gezaehlt unter `htf_daily_filter_matrix`.

Risiko (auf der besten Ausstiegs-Variante nach IS-t): fest 1 % | Konfluenz-Staffel (Plan C1): Score = Zahl
der weiteren Makrofilter „mit“ (M1 Zins-Momentum, M2 Carry, M3 Regime-Matrix, M6 G8, X2 DXY);
0-1 → 0,5 %, 2-3 → 1 %, 4-5 → 2 %.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.backtest_varianten import entries
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, OOS_END, WARMUP, load_market
from research_lock import Lock, deflated_sharpe

LOCK = "htf_daily_filter_matrix"
STOPS = ("S1", "S2", "S3", "S4")
EXITS = {  # Beine: (Anteil, Ziel)
    "A0": [(1.0, "zeit")], "A1": [(1.0, "2R")], "A2": [(1.0, "3R")], "A3": [(1.0, "liq")], "A4": [(1.0, "trail")],
    "A5": [(0.5, "2R"), (0.5, "zeit")], "A6": [(0.5, "3R"), (0.5, "trail")], "A7": [(0.5, "2R"), (0.5, "liq")],
    "A8": [(1 / 3, "1R"), (1 / 3, "2R"), (1 / 3, "zeit")], "A9": [(0.5, "1R"), (0.5, "zeit")],
}
BES = {"B0": None, "B1": 1.0, "B2": 1.5}
HOLD = {"zeit": 10, "trail": 30}
SCORE_FILTERS = ("M1", "M2", "M3", "M6", "X2")
START_KAPITAL = 100_000.0


def candidate() -> pd.DataFrame:
    t = pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"])
    t = t[t["setup"] == "C2"].copy()
    t["RS"] = commodity_state(t)
    t = t[(t["T6"] == "gegen") & (t["M7"] == "mit") & (t["RS"] != "gegen")].copy()
    t["score"] = (t[list(SCORE_FILTERS)] == "mit").sum(axis=1)
    return t


def sim(x: pd.DataFrame, en: dict, stop_kind: str, legs: list, be: float | None, cost: float, end_idx: int):
    h, l, c = x["High"].to_numpy(), x["Low"].to_numpy(), x["Close"].to_numpy()
    sign = 1 if en["side"] == "long" else -1
    entry, f, atr = en["price"], en["fill"], en["atr"]
    prev = f - 1 if en["start"] == f else f
    stop = {"S1": en["struct"], "S2": entry - sign * 2 * atr, "S3": entry - sign * atr,
            "S4": l[prev] if sign == 1 else h[prev]}[stop_kind]
    risk = sign * (entry - stop)
    if not (risk > 0) or not np.isfinite(risk):
        return None
    lk = 20
    liq = h[max(0, f - lk):f].max() if sign == 1 else l[max(0, f - lk):f].min()
    if sign * (liq - entry) < risk:          # Liquiditaet naeher als 1 R oder hinter dem Einstieg -> 3 R
        liq = entry + sign * 3 * risk
    targets = {"1R": entry + sign * risk, "2R": entry + sign * 2 * risk, "3R": entry + sign * 3 * risk, "liq": liq}
    open_legs = [[frac, kind, HOLD.get(kind, 15)] for frac, kind in legs]
    pnl, cur_stop, last_k = 0.0, stop, f
    max_last = min(end_idx, f + max(leg[2] for leg in open_legs))
    for k in range(en["start"], max_last + 1):
        last_k = k
        if (sign == 1 and l[k] <= cur_stop) or (sign == -1 and h[k] >= cur_stop):
            pnl += sum(leg[0] for leg in open_legs) * sign * (cur_stop - entry)
            open_legs = []
            break
        if k == f and en.get("limit"):
            continue
        still = []
        for leg in open_legs:
            frac, kind, hold = leg
            tg = targets.get(kind)
            if tg is not None and ((sign == 1 and h[k] >= tg) or (sign == -1 and l[k] <= tg)):
                pnl += frac * sign * (tg - entry)
            elif kind == "trail" and k > f and ((sign == 1 and c[k] < l[k - 1]) or (sign == -1 and c[k] > h[k - 1])):
                pnl += frac * sign * (c[k] - entry)
            elif k >= min(end_idx, f + hold):
                pnl += frac * sign * (c[k] - entry)
            else:
                still.append(leg)
        open_legs = still
        if not open_legs:
            break
        if be is not None and cur_stop != entry and sign * ((h[k] if sign == 1 else l[k]) - entry) >= be * risk:
            cur_stop = entry
    if open_legs:
        pnl += sum(leg[0] for leg in open_legs) * sign * (c[last_k] - entry)
    return {"r": (pnl - cost) / risk, "exit_k": last_k}


def run_all(cand: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    keys = {(r.markt, r.datum.normalize(), r.seite): r for r in cand.itertuples()}
    variants = list(itertools.product(STOPS, EXITS, BES))
    out = {v: [] for v in variants}
    e = pd.Timestamp(OOS_END)
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):e], grid)
        end_idx = int(np.searchsorted(x.index, e, side="right")) - 1
        used = set()
        for en in sorted((z for z in entries(x, "C") if z["v"] == "C2 EL"), key=lambda z: z["fill"]):
            key = (name, x.index[en["fill"]].normalize(), en["side"])
            r = keys.get(key)
            if r is None or key in used:   # wie die Basis: ein Einstieg je Markt, Tag und Richtung
                continue
            used.add(key)
            for v in variants:
                res = sim(x, en, v[0], EXITS[v[1]], BES[v[2]], cost, end_idx)
                if res is not None:
                    out[v].append({"markt": name, "datum": r.datum, "periode": r.periode, "r": res["r"],
                                   "exit_datum": x.index[res["exit_k"]], "score": r.score})
    rows = []
    for v, tr in out.items():
        t = pd.DataFrame(tr)
        row = {"variante": " ".join(v)}
        for per in ("IS", "OOS"):
            st = stats(t.loc[t["periode"] == per, "r"])
            row.update({f"{per}_n": st.get("n"), f"{per}_mean": st.get("mean_r"), f"{per}_t": st.get("t"),
                        f"{per}_treffer": st.get("treffer"), f"{per}_pf": st.get("pf")})
        rows.append(row)
    return pd.DataFrame(rows), {" ".join(v): pd.DataFrame(tr) for v, tr in out.items()}


def konto(t: pd.DataFrame, risk_of) -> dict:
    t = t.sort_values("datum").reset_index(drop=True)
    eq, offen, kurve = START_KAPITAL, [], []
    for x in t.itertuples():
        for o in [o for o in offen if o[0] < x.datum]:
            eq += o[1]
            offen.remove(o)
            kurve.append(eq)
        offen.append((x.exit_datum, eq * risk_of(x) * x.r))
    for o in sorted(offen):
        eq += o[1]
        kurve.append(eq)
    k = pd.Series([START_KAPITAL] + kurve)
    jahre = (t["exit_datum"].max() - t["datum"].min()).days / 365.25
    return {"ende": eq, "cagr": (eq / START_KAPITAL) ** (1 / jahre) - 1, "max_dd": (k / k.cummax() - 1).min()}


def main() -> None:
    cand = candidate()
    res, trades = run_all(cand)
    lock = Lock(LOCK)
    if lock.trials < 568:   # 119 Varianten einmal gezaehlt (11.11.); Neulauf nach Fix der Doppel-Einstiege zaehlt nicht neu
        lock.log_trials(len(res) - 1, "Kandidat C2+Faber gegen+COT mit+Rohstoff-Veto: Stop x Ausstieg/Teilgewinne x BE (11.11.)")
    res["dsr"] = [deflated_sharpe(r.IS_t / np.sqrt(r.IS_n), int(r.IS_n), lock.trials) for r in res.itertuples()]
    res.to_csv("htf_daily_trade/c2_exit_varianten.csv", index=False)
    pd.set_option("display.width", 220)
    base = res[res["variante"] == "S1 A0 B0"]
    print(f"Lock {LOCK}: {lock.trials} Versuche. Basis S1 A0 B0:")
    print(base.round(3).to_string(index=False))
    srt = res.sort_values("IS_t", ascending=False)
    print(f"\n== Top 15 nach IS-t (von {len(res)}) ==")
    print(srt.head(15).round(3).to_string(index=False))
    for dim, pos in (("Stop", 0), ("Ausstieg", 1), ("BE", 2)):
        key = res["variante"].str.split().str[pos]
        g = res.groupby(key)[["IS_mean", "OOS_mean"]].mean()
        print(f"\nØ je {dim}: " + " | ".join(f"{k} IS {a:+.3f} OOS {b:+.3f}" for k, (a, b) in g.iterrows()))

    best = srt.iloc[0]["variante"]
    for label, v in (("Basis S1 A0 B0", "S1 A0 B0"), (f"IS-Beste {best}", best)):
        t = trades[v]
        print(f"\n== Risiko auf {label} (IS + OOS 2016-2024, 100k) ==")
        print("Ø R je Konfluenz-Score: " + ", ".join(
            f"{s}: n {len(g)} Ø {g['r'].mean():+.2f}" for s, g in t.groupby("score")))
        fest = konto(t, lambda x: 0.01)
        staffel = konto(t, lambda x: 0.005 if x.score <= 1 else (0.01 if x.score <= 3 else 0.02))
        for n, k in (("fest 1 %", fest), ("Staffel 0,5/1/2 %", staffel)):
            print(f"{n:<18} Ende {k['ende']:>10,.0f}  CAGR {k['cagr']:+.1%}  max. DD {k['max_dd']:.1%}")
        wk = t.groupby(t["datum"].dt.to_period("W")).size()
        print(f"Trades je Woche: max {wk.max()}, Wochen mit > 2 Einstiegen: {(wk > 2).sum()}")


if __name__ == "__main__":
    main()
