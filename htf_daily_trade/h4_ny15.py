"""H4-Manipulation nur zur NY-Session: Einstieg 15:00 deutscher Zeit (Nutzerauftrag 12.11.2026).

    python -m htf_daily_trade.h4_ny15

Lock `h4_manip` (gleicher Split wie h4_manip: IS 2016-21, OOS bis 11.05.2026, Tresor/Blind zu).
Signalkerze = H4 12-16 Uhr Serverzeit (NY 05-09, 11-15 Uhr deutsch); Einstieg ab Kerze 16 Uhr Server = 15:00 deutsch
= 09:00 New York.
Signal N2/N3/N4: Docht ueber/unter Hoch/Tief der N Vorkerzen, KOERPER (Open und Close) wieder innerhalb dieser Marke.
Docht W00/W40/W50/W60/W70: Docht in Sweep-Richtung >= x % der Kerzenspanne.
Einstieg EM Market 15:00 | LW Limit 50 % des Dochts | LS Limit an der gesweepten Marke (je 6 H4-Kerzen gueltig).
Stop S1 Docht-Extrem | S2 + 0,2 ATR(H4) | S3 + 0,5 ATR(H4).
Ziel R2 2 R | R3 3 R | TB naechstes H4-Swing | TC Vortag/Vorwoche | TE Tagesende (NY 17:00 = Server 24:00).
Ohne BE (B1 brachte im ersten H4-Test nichts). Kosten Round-Trip + TTP-Swap. Ein Signal je Tag und Markt; Trades
duerfen sich ueberlappen. Auswertung gesamt, FX und Metalle getrennt; Filter-Stufe nur fuer die Top-3 je Klasse.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.filter_matrix import MARKETS, METALS, MacroDirs, extra_dirs
from htf_daily_trade.h4_manip import IS_END, IS_START, LOCK, MAX_HOLD, OOS_END, Market, daily
from htf_daily_trade.twin_trade import swap_r
from research_lock import Lock, deflated_sharpe

SIGNAL_HOUR = 12           # Serverzeit-Beginn der Signalkerze
NS, WS = (2, 3, 4), (0.0, 0.4, 0.5, 0.6, 0.7)
ENTRIES, STOPS, TARGETS = ("EM", "LW", "LS"), ("S1", "S2", "S3"), ("R2", "R3", "TB", "TC", "TE")
STOP_ATR = {"S1": 0.0, "S2": 0.2, "S3": 0.5}
LIMIT_BARS = 6
FILTERS = {"T1": "MA 12/20", "T2": "Weekly SMA 20/50", "T3": "SMA 200", "T4": "ADX DI", "T5": "Ribbon", "T6": "Faber",
           "T7": "Weekly EMA 9/21", "D": "Daily-Struktur", "H4": "H4-Struktur", "X2": "DXY 20T", "X3": "Realzins",
           "X4": "COT-Index konträr", "X5": "Kalman", "X6": "Triple-MA", "X9": "USD breit", "X10": "Partner",
           "M1": "Zins-Momentum", "M2": "Carry", "M3": "Regime-Matrix", "M6": "G8-Stärke", "M7": "COT-Fluss"}
N_BASE = len(NS) * len(WS) * len(ENTRIES) * len(STOPS) * len(TARGETS)
TOP_FILTER = 3


def h4_atr(m: Market, n: int = 14) -> np.ndarray:
    pc = np.r_[np.nan, m.c[:-1]]
    tr = np.nanmax(np.vstack([m.h - m.l, np.abs(m.h - pc), np.abs(m.l - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def signals(m: Market, atr: np.ndarray) -> list[dict]:
    out = []
    hrs = m.srv.hour
    for k in np.flatnonzero(hrs == SIGNAL_HOUR):
        if k < 5 or k + 1 >= len(m.x):
            continue
        o, h, l, c = m.o[k], m.h[k], m.l[k], m.c[k]
        rng = h - l
        if rng <= 0:
            continue
        for side in ("long", "short"):
            ns = []
            for n in NS:
                if side == "long":
                    lvl = m.l[k - n:k].min()
                    ok = l < lvl and min(o, c) > lvl
                else:
                    lvl = m.h[k - n:k].max()
                    ok = h > lvl and max(o, c) < lvl
                if ok:
                    ns.append((n, lvl))
            if not ns:
                continue
            wick = (min(o, c) - l) / rng if side == "long" else (h - max(o, c)) / rng
            out.append({"k": int(k), "side": side, "ns": ns, "wick": wick,
                        "wick_atr": (min(o, c) - l if side == "long" else h - max(o, c)) / atr[k],
                        "ext": l if side == "long" else h, "body": min(o, c) if side == "long" else max(o, c)})
    return out


def simulate(m: Market, s: dict, entry_kind: str, lvl: float | None, stop_kind: str, tgt_kind: str,
             atr: np.ndarray, end_idx: int):
    k, sign = s["k"], 1 if s["side"] == "long" else -1
    stop = s["ext"] - sign * STOP_ATR[stop_kind] * atr[k]
    if entry_kind == "EM":
        f, entry, limit = k + 1, m.o[k + 1], False
    else:
        f = next((j for j in range(k + 1, min(end_idx, k + LIMIT_BARS) + 1)
                  if (sign == 1 and m.l[j] <= lvl) or (sign == -1 and m.h[j] >= lvl)), None)
        if f is None:
            return None
        entry, limit = (min(m.o[f], lvl) if sign == 1 else max(m.o[f], lvl)), True
    risk = sign * (entry - stop)
    if not (risk > 0):
        return None
    if tgt_kind in ("R2", "R3"):
        tgt = entry + sign * (2 if tgt_kind == "R2" else 3) * risk
    elif tgt_kind == "TE":
        tgt = None
    else:
        tgt = m.target(tgt_kind, sign, entry, risk, f - 1, f)
    if tgt_kind == "TE":
        day = m.day[f]
        last = f
        while last + 1 <= end_idx and m.day[last + 1] == day:
            last += 1
    else:
        last = min(end_idx, f + MAX_HOLD - 1)
    px, j = None, f
    for j in range(f, last + 1):
        if (sign == 1 and m.l[j] <= stop) or (sign == -1 and m.h[j] >= stop):
            px = stop
            break
        if limit and j == f:
            continue
        if tgt is not None and ((sign == 1 and m.h[j] >= tgt) or (sign == -1 and m.l[j] <= tgt)):
            px = tgt
            break
    if px is None:
        j, px = last, m.c[last]
    gross = sign * (px - entry) / risk
    sw = swap_r(m.name, s["side"], entry, risk, m.x.index[f].tz_localize(None), m.x.index[j].tz_localize(None))
    return gross, gross - m.cost / risk - sw, m.x.index[f].tz_localize(None), m.x.index[j].tz_localize(None)


def filter_states(m: Market, name: str, sigs: list[dict], md: MacroDirs) -> list[dict]:
    d = daily(name).loc[:pd.Timestamp(OOS_END)]
    fx = features(d, MARKETS[name][1])
    ex = extra_dirs(name, fx)
    out = []
    for s in sigs:
        sign = 1 if s["side"] == "long" else -1
        day = m.day[s["k"]]
        pos = d.index.searchsorted(day) - 1
        st = {f: m.state(f, s["k"], sign) for f in ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "D", "H4")}
        raw = {f: (ex[f].iat[pos] if pos >= 0 else 0) for f in ("X2", "X5", "X6", "X9", "X10")}
        raw.update({f: v for f, v in md.dirs(name, day).items() if f in FILTERS})
        e = md.extra(name, day)
        raw.update({"X3": e["X3"], "X4": e["X4"]})
        for f, v in raw.items():
            v = int(np.sign(v or 0)) * sign
            st[f] = "mit" if v > 0 else "gegen" if v < 0 else "neutral"
        out.append(st)
    return out


def run_market(name: str, md: MacroDirs) -> pd.DataFrame:
    m = Market(name, OOS_END)
    atr = h4_atr(m)
    end_idx = len(m.x) - 1
    start = int(m.x.index.searchsorted(pd.Timestamp(IS_START, tz="UTC")))
    sigs = [s for s in signals(m, atr) if s["k"] >= start]
    states = filter_states(m, name, sigs, md)
    rows = []
    for s, st in zip(sigs, states):
        base = {"markt": name, "klasse": "Metalle" if name in METALS else "FX", "seite": s["side"],
                "wick": s["wick"], "wick_atr": s["wick_atr"], "ns": ",".join(str(n) for n, _ in s["ns"]), **st}
        levels = {"EM": [(None, None)], "LW": [(None, (s["body"] + s["ext"]) / 2)],
                  "LS": [(n, lvl) for n, lvl in s["ns"]]}
        for e, sk, tk in itertools.product(ENTRIES, STOPS, TARGETS):
            for n_lvl, lvl in levels[e]:
                res = simulate(m, s, e, lvl, sk, tk, atr, end_idx)
                if res is None:
                    continue
                rows.append({**base, "e": e, "s": sk, "t": tk, "n_lvl": n_lvl, "r_brutto": res[0], "r": res[1],
                             "einstieg": res[2], "ausstieg": res[3]})
    return pd.DataFrame(rows)


def select(t: pd.DataFrame, n: int, w: float, e: str, s: str, tk: str) -> pd.DataFrame:
    g = t[(t["e"] == e) & (t["s"] == s) & (t["t"] == tk) & (t["wick"] >= w) & t["ns"].str.contains(str(n))]
    return g[g["n_lvl"] == n] if e == "LS" else g


def summary(g: pd.DataFrame, n_trials: int) -> dict:
    row = {}
    for per in ("IS", "OOS"):
        p = g[g["periode"] == per]
        st = stats(p["r"])
        row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                    f"{per}_brutto": p["r_brutto"].mean(), f"{per}_treffer": (p["r"] > 0).mean()})
    i = g.loc[g["periode"] == "IS", "r"]
    row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), n_trials) if len(i) > 2 else np.nan
    row["jahre+"] = f"{(g.groupby(g['einstieg'].dt.year)['r'].mean() > 0).sum()}/{g['einstieg'].dt.year.nunique()}"
    row["maerkte+"] = f"{(g.groupby('markt')['r'].mean() > 0).sum()}/{g['markt'].nunique()}"
    if len(g) > 5:
        k = konto(g.rename(columns={"einstieg": "datum", "ausstieg": "exit_datum"})[["datum", "exit_datum", "r"]], lambda x: 0.01)
        row.update({"cagr": k["cagr"], "dd": k["max_dd"]})
    return row


def main() -> None:
    lock = Lock(LOCK)
    n_new = N_BASE * 3 + 2 * TOP_FILTER * 2 * len(FILTERS)
    if lock.trials <= 456:
        lock.log_trials(n_new, f"NY 15:00: {N_BASE} Grundvarianten x 3 Universen + Filter (Top {TOP_FILTER} je Klasse x "
                               f"{len(FILTERS)} x mit/gegen) (12.11.)")
    print(f"Lock {LOCK}: {lock.trials} Versuche", flush=True)
    md = MacroDirs.full()
    t = pd.concat([run_market(n, md) for n in MARKETS], ignore_index=True)
    t["periode"] = np.where(t["einstieg"] <= pd.Timestamp(IS_END) + pd.Timedelta(hours=23, minutes=59), "IS", "OOS")
    t.to_parquet("htf_daily_trade/h4_ny15_trades.parquet", index=False)
    pd.set_option("display.width", 260)
    rows = []
    for (n, w, e, s, tk) in itertools.product(NS, WS, ENTRIES, STOPS, TARGETS):
        g = select(t, n, w, e, s, tk)
        for uni, gg in (("alle", g), ("FX", g[g["klasse"] == "FX"]), ("Metalle", g[g["klasse"] == "Metalle"])):
            rows.append({"variante": f"N{n} W{int(w * 100):02d} {e} {s} {tk}", "universum": uni,
                         **summary(gg, lock.trials)})
    res = pd.DataFrame(rows)
    res.to_csv("htf_daily_trade/h4_ny15_varianten.csv", index=False)
    cols = ["variante", "IS_n", "IS_R", "IS_t", "IS_brutto", "IS_treffer", "OOS_n", "OOS_R", "OOS_t", "OOS_brutto",
            "dsr", "jahre+", "maerkte+", "cagr", "dd"]
    for uni in ("alle", "FX", "Metalle"):
        r = res[(res["universum"] == uni) & (res["IS_n"] >= 60)].sort_values("IS_t", ascending=False)
        print(f"\n== {uni}: Top 15 nach IS-t (von {len(r)}) ==\n" + r[cols].head(15).round(3).to_string(index=False))
    parts = res["variante"].str.split(expand=True)
    for i, dim in enumerate(("Sweep-Kerzen", "Docht", "Einstieg", "Stop", "Ziel")):
        g = res.assign(dim=parts[i]).groupby(["dim", "universum"])[["IS_R", "OOS_R", "IS_brutto", "OOS_brutto"]].mean()
        print(f"\nØ je {dim}:\n{g.unstack().round(3).to_string()}")
    ref = t[(t["e"] == "EM") & (t["s"] == "S1") & (t["t"] == "R3")]
    for col in ("wick", "wick_atr"):
        q = pd.qcut(ref[col], 5, duplicates="drop")
        g = ref.groupby([q, "periode"], observed=True)["r_brutto"].agg(["size", "mean"]).unstack().round(3)
        print(f"\nDocht-Länge ({col}) in Quintilen, EM S1 3R, R brutto:\n{g.to_string()}")
    frows = []
    for uni in ("FX", "Metalle"):
        r = res[(res["universum"] == uni) & (res["IS_n"] >= 60)].sort_values("IS_t", ascending=False).head(TOP_FILTER)
        for v in r["variante"]:
            n, w, e, s, tk = v.split()
            g = select(t, int(n[1:]), int(w[1:]) / 100, e, s, tk)
            g = g[g["klasse"] == uni]
            for f in FILTERS:
                for z in ("mit", "gegen"):
                    sel = g[g[f] == z]
                    if (sel["periode"] == "IS").sum() >= 30:
                        frows.append({"universum": uni, "variante": v, "filter": f"{f} {FILTERS[f]} {z}",
                                      **summary(sel, lock.trials)})
    fr = pd.DataFrame(frows).sort_values("IS_t", ascending=False)
    fr.to_csv("htf_daily_trade/h4_ny15_filter.csv", index=False)
    for uni in ("FX", "Metalle"):
        print(f"\n== Filter {uni}: Top 15 nach IS-t ==\n"
              + fr[fr["universum"] == uni][["variante", "filter"] + cols[1:]].head(15).round(3).to_string(index=False))
    for uni in ("FX", "Metalle"):
        best = res[(res["universum"] == uni) & (res["IS_n"] >= 60)].sort_values("IS_t", ascending=False).iloc[0]["variante"]
        n, w, e, s, tk = best.split()
        g = select(t, int(n[1:]), int(w[1:]) / 100, e, s, tk)
        g = g[g["klasse"] == uni]
        print(f"\n{uni} beste {best} je Markt:\n"
              + g.groupby(["markt", "periode"])["r"].agg(["size", "mean"]).unstack().round(3).to_string())


if __name__ == "__main__":
    main()
