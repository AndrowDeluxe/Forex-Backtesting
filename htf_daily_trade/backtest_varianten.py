"""Einstiegs-, Stop- und Ziel-Varianten fuer Typ R und Typ C -- nur IS 2016-2021 (Nutzer 02.11.2026).

    python -m htf_daily_trade.backtest_varianten

Ohne Confi-Gate und ohne Makro (beides half im IS nicht). Alle Kombinationen gezaehlt:
Typ R (Lock `htf_daily_trade_r`): E1/E2/E3 x S1-S4 x T1-T8 = 96.
Typ C (Lock `htf_daily_trade_c`): C1/C2 x Eroeffnung/Limit x S1-S4 x T1-T8 = 128.

Einstieg  E1 Schluss jenseits der Fractal-Kerze | E2 Eroeffnung nach Bestaetigung (00:01) |
          E3 Limit auf 50 % der Fractal-Kerze, 3 Tage gueltig (Typ C: 50 % der Signalkerze)
Stop      S1 Struktur (Fractal / Manipulation) | S2 2x ATR | S3 1x ATR | S4 Extrem der letzten
          abgeschlossenen Tageskerze vor dem Einstieg
Ziel      T1 1,5 R | T2 2 R | T3 3 R | T4 2x ATR | T5 4x ATR (T1-T5 max. 15 Tage) |
          T6 Nachziehen: Schluss unter Vortagestief | T7 gegenlaeufiges Fractal bestaetigt
          (T6/T7 max. 30 Tage) | T8 nur Zeit: Schluss nach 10 Tagen
Tageskerzen, Stop/Ziel intrabar; trifft eine Kerze beides, zaehlt der Stop. In der Fuell-Kerze
eines Limits zaehlt nur der Stop. Kosten Spread+Kommission, kein Swap.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_macro import c_signals
from htf_daily_trade.backtest_r import MARKETS, features, load_market, signals, stats
from research_lock import Lock, deflated_sharpe

STOPS = ("S1", "S2", "S3", "S4")
TARGETS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")
R_VARIANTS = list(itertools.product(("E1", "E2", "E3"), STOPS, TARGETS))
C_VARIANTS = list(itertools.product(("C1", "C2"), ("EO", "EL"), STOPS, TARGETS))
LIMIT_DAYS = 3


def entries(x: pd.DataFrame, typ: str) -> list[dict]:
    """Einheitliche Einstiege: side, fill (Index), price, struct (Strukturstop), atr, same_bar_target."""
    h, l, o = x["High"].to_numpy(), x["Low"].to_numpy(), x["Open"].to_numpy()
    n = len(x)
    out = []

    def limit_fill(side, start, lvl):
        for k in range(start, min(n, start + LIMIT_DAYS)):
            if side == "long" and l[k] <= lvl:
                return k, min(o[k], lvl)
            if side == "short" and h[k] >= lvl:
                return k, max(o[k], lvl)
        return None, None

    if typ == "R":
        for s in signals(x):
            i, side = s["i"], s["side"]
            if s["etype"] == "E1":
                out.append(dict(v="E1", side=side, fill=s["e"], price=s["entry"], struct=s["frac_lvl"],
                                atr=s["atr"], start=s["e"] + 1))
            else:
                out.append(dict(v="E2", side=side, fill=s["e"], price=s["entry"], struct=s["frac_lvl"],
                                atr=s["atr"], start=s["e"]))
                mid = (h[i] + l[i]) / 2
                k, px = limit_fill(side, i + 3, mid)
                if k is not None:
                    out.append(dict(v="E3", side=side, fill=k, price=px, struct=s["frac_lvl"],
                                    atr=s["atr"], start=k, limit=True))
    else:
        for s in c_signals(x):
            t, side = s["i"], s["side"]
            out.append(dict(v=f"{s['kind']} EO", side=side, fill=s["e"], price=s["entry"],
                            struct=s["frac_lvl"], atr=s["atr"], start=s["e"]))
            mid = (h[t] + l[t]) / 2 if s["kind"] == "C1" else (x["Close"].iat[t] + s["frac_lvl"]) / 2
            k, px = limit_fill(side, t + 1, mid)
            if k is not None:
                out.append(dict(v=f"{s['kind']} EL", side=side, fill=k, price=px, struct=s["frac_lvl"],
                                atr=s["atr"], start=k, limit=True))
    return out


def simulate(x, en, stop_kind, tgt, cost, end_idx):
    h, l, c = x["High"].to_numpy(), x["Low"].to_numpy(), x["Close"].to_numpy()
    fh, fl = x["frac_hi"].to_numpy(), x["frac_lo"].to_numpy()
    sign = 1 if en["side"] == "long" else -1
    entry, f, atr = en["price"], en["fill"], en["atr"]
    prev = f - 1 if en["start"] == f else f      # letzte abgeschlossene Kerze vor dem Einstieg
    stop = {"S1": en["struct"], "S2": entry - sign * 2 * atr, "S3": entry - sign * atr,
            "S4": l[prev] if sign == 1 else h[prev]}[stop_kind]
    risk = sign * (entry - stop)
    if not (risk > 0) or not np.isfinite(risk):
        return None
    target = {"T1": entry + sign * 1.5 * risk, "T2": entry + sign * 2 * risk, "T3": entry + sign * 3 * risk,
              "T4": entry + sign * 2 * atr, "T5": entry + sign * 4 * atr}.get(tgt)
    max_hold = {"T6": 30, "T7": 30, "T8": 10}.get(tgt, 15)
    last = min(end_idx, f + max_hold)
    exit_px, k = None, en["start"]
    for k in range(en["start"], last + 1):
        if (sign == 1 and l[k] <= stop) or (sign == -1 and h[k] >= stop):
            exit_px = stop
            break
        if k == f and en.get("limit"):
            continue
        if target is not None and ((sign == 1 and h[k] >= target) or (sign == -1 and l[k] <= target)):
            exit_px = target
            break
        if tgt == "T6" and k > f and ((sign == 1 and c[k] < l[k - 1]) or (sign == -1 and c[k] > h[k - 1])):
            exit_px = c[k]
            break
        if tgt == "T7" and k - 2 > f and ((sign == 1 and fh[k - 2]) or (sign == -1 and fl[k - 2])):
            exit_px = c[k]
            break
    if exit_px is None:
        k = last
        exit_px = c[k]
    return {"r": (sign * (exit_px - entry) - cost) / risk, "exit_k": k}


def run(data, variant_pred, stop_kind, tgt, is_start, is_end):
    rows = []
    for name, (x, ens, cost) in data.items():
        end_idx = int(np.searchsorted(x.index, is_end, side="right")) - 1
        busy = {"long": -1, "short": -1}
        for en in sorted((e for e in ens if variant_pred(e)), key=lambda e: e["fill"]):
            t = x.index[en["fill"]]
            if t < is_start or t > is_end or en["fill"] > end_idx or en["fill"] <= busy[en["side"]]:
                continue
            res = simulate(x, en, stop_kind, tgt, cost, end_idx)
            if res is None:
                continue
            busy[en["side"]] = res["exit_k"]
            rows.append({"markt": name, "datum": t.date(), "seite": en["side"], "r": res["r"]})
    return pd.DataFrame(rows)


def summarize(title, rows, trades, lock, out_csv):
    res = pd.DataFrame(rows).sort_values("t", ascending=False)
    res.to_csv(out_csv, index=False)
    pd.set_option("display.width", 180)
    print(f"\n===== {title}: Top 12 von {len(res)} (Lock jetzt {lock.trials} Versuche) =====")
    print(res.head(12).round(3).to_string(index=False))
    print(f"Varianten mit t > 2: {(res.t > 2).sum()}  |  Ø R > 0: {(res.mean_r > 0).sum()} von {len(res)}")
    best = res.iloc[0]
    tb = trades[best["variante"]]
    sr = tb["r"].mean() / tb["r"].std(ddof=1)
    print(f"Beste {best['variante']}: n {len(tb)}, Deflated Sharpe {deflated_sharpe(sr, len(tb), lock.trials):.3f}")
    print(tb.groupby("markt")["r"].agg(["size", "mean"]).round(2).T.to_string())
    print(tb.groupby(pd.to_datetime(tb["datum"]).dt.year)["r"].agg(["size", "mean"]).round(2).T.to_string())
    for dim, pos in (("Einstieg", 0), ("Stop", -2), ("Ziel", -1)):
        key = res["variante"].str.split().str[pos] if pos != 0 else res["variante"].str.rsplit(n=2).str[0]
        print(f"Ø mean_r je {dim}: " + ", ".join(f"{k} {v:+.3f}" for k, v in res.groupby(key)["mean_r"].mean().items()))


def main() -> None:
    lr, lc = Lock("htf_daily_trade_r"), Lock("htf_daily_trade_c")
    if lr.trials < 56 + len(R_VARIANTS):
        lr.log_trials(len(R_VARIANTS), "Typ R Varianten E1-E3 x S1-S4 x T1-T8 ohne Gate/Makro (02.11.)")
    if lc.trials < 24 + len(C_VARIANTS):
        lc.log_trials(len(C_VARIANTS), "Typ C Varianten C1/C2 x EO/EL x S1-S4 x T1-T8 ohne Makro (02.11.)")
    is_start, is_end = pd.Timestamp("2016-01-01"), pd.Timestamp("2021-12-31")
    dr, dc = {}, {}
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp("2015-01-01"):is_end], grid)
        dr[name] = (x, entries(x, "R"), cost)
        dc[name] = (x, entries(x, "C"), cost)
    for title, data, variants, lock, csv in (
            ("Typ R", dr, R_VARIANTS, lr, "htf_daily_trade/varianten_r_is.csv"),
            ("Typ C", dc, C_VARIANTS, lc, "htf_daily_trade/varianten_c_is.csv")):
        rows, trades = [], {}
        for var in variants:
            ent = " ".join(var[:-2])
            t = run(data, lambda e, ent=ent: e["v"] == ent, var[-2], var[-1], is_start, is_end)
            key = " ".join(var)
            trades[key] = t
            rows.append({"variante": key, **(stats(t["r"]) if len(t) > 1 else {"n": len(t), "t": np.nan})})
        summarize(title, rows, trades, lock, csv)


if __name__ == "__main__":
    main()
