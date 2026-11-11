"""Twin-Trade: Daily-Order direkt + Limit-Bein(e) zu besserem Preis mit groesserem Stop (Nutzerauftrag 11.11.2026,
Plan freigegeben).

    python -m htf_daily_trade.twin_trade          # IS 2016-2021 + OOS 2022-2024 (2025/Tresor zu)

Ideen: ltf_entry.daily_ideas() (eingefrorene Daily-Regeln, 10 Handelstage gueltig).
Daily-Bein D: Markt zur Eroeffnung nach dem Signaltag (C2 EO), Strukturstop, Schluss am Ideen-Ende.
Limit-Beine (gueltig bis Ideen-Ende, long tiefer / short hoeher als der Daily-Einstieg):
  P1 50 % Signalkerze | P2 Fib 61,8 % | P3 Fib 78,6 % | P4 50 % Vorwochen-Range | P5 Fib 61,8 % Vorwoche
  P6 Leiter 50 % + 78,6 % | P7 Leiter 50 % + 61,8 % + 78,6 %
  L1 M15 Sweep+CHoCH | L2 M15 Doppel-BOS | L3 M15 FVG-Limit | L5 CRT auf H1 (Einstieg M15)
  C  CTNL: H1 Doppel-BOS in Ideen-Richtung, dann M15 Sweep-and-Reject des H1-Levels zum ersten BOS
  M  H1-Liq-Spike (Sweep-and-Reject des letzten H1-Swings), dann M5-CHoCH binnen 12 Kerzen (6 FX + Gold bis 08/2024)
  LTF-Typen mit 1 oder bis zu 3 Einstiegen je Idee.
Stop Limit-Beine: SA Daily-Strukturstop + 0,5 x ATR | SB Daily-Strukturstop | SC 1,5 x ATR ab Einstieg.
Ausstieg Limit-Beine: XA Ideen-Ende | XB Tagesziel (Vortageshoch/-tief, sonst Daily-Fractal, sonst 3 R; max. Ideen-Ende).
Risiko: RA gesamt 1 % gleich auf alle geplanten Beine | RB jedes Bein 1 %.
Kosten je Bein: Spread+Kommission + TTP-Swap. Stop vor Ziel; Fuellkerze eines Limits nur Stop.
Sperre `htf_daily_twin`, alle 228 Varianten gezaehlt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.structure import compute_market_structure
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.c2_kandidat_report import AUFSCHLAG, CCY, rates
from htf_daily_trade.filter_matrix import MARKETS, WARMUP, load_market
from htf_daily_trade.ltf_entry import IS_END, RUN_END, daily_ideas, load_ltf, sim_one, trigger_events
from fusion_lab.patterns import crt
from research_lock import Lock, deflated_sharpe

LOCK = "htf_daily_twin"
PRICE = {"P1": [0.5], "P2": [0.618], "P3": [0.786], "P4": [("w", 0.5)], "P5": [("w", 0.618)],
         "P6": [0.5, 0.786], "P7": [0.5, 0.618, 0.786]}
LTF_TYPES = ("L1", "L2", "L3", "L5", "C", "M")
ENTRIES = list(PRICE) + [f"{t} x{a}" for t in LTF_TYPES for a in (1, 3)]
STOPS, EXITS, RISKS = ("SA", "SB", "SC"), ("XA", "XB"), ("RA", "RB")
M5_FILES = {"XAUUSD": ["GOLD_M5_2016-01-01_2024-08-01.parquet"]}
M5_CHOCH_BARS = 12
_rt = None


def swap_r(name, side, entry, risk, d0, d1):
    global _rt
    if _rt is None:
        _rt = rates()
    base, quote = CCY[name]
    row = _rt.loc[:d0].iloc[-1]
    diff = row[quote] - (row[base] if base else 0.0)
    mk = AUFSCHLAG["TTP"][1 if base is None else 0]
    days = max(0, (pd.Timestamp(d1).normalize() - pd.Timestamp(d0).normalize()).days)
    return ((diff if side == "long" else -diff) + mk) / 365 * days * entry / risk


def leg_stop(kind, sign, entry, dstop, atr):
    s = {"SA": dstop - sign * 0.5 * atr, "SB": dstop, "SC": entry - sign * 1.5 * atr}[kind]
    return s if sign * (entry - s) > 0 else None


def day_target(x, k_day, sign, entry, risk, frac_lvls):
    lvl = x["High"].iat[k_day - 1] if sign == 1 else x["Low"].iat[k_day - 1]
    if sign * (lvl - entry) >= risk:
        return lvl
    return next((f for f in frac_lvls if sign * (f - entry) >= risk), entry + sign * 3 * risk)


# --------------------------------------------------------------------------- Daily-Ebene (D und P-Limits)
def daily_legs(x, idea, t, cost):
    """Gibt {'D': leg, ('P1',stop,exit): [legs], ...} mit leg = (r, entry_datum, exit_datum) oder None."""
    h, l, o, c = (x[k].to_numpy() for k in ("High", "Low", "Open", "Close"))
    n = len(x)
    sign = 1 if idea.seite == "long" else -1
    end = min(n - 1, t + 10)
    name = idea.markt
    out = {}

    def run(fill, entry, stop, target, limit):
        a = fill if limit else fill
        for k in range(a, end + 1):
            if (sign == 1 and l[k] <= stop) or (sign == -1 and h[k] >= stop):
                return k, stop
            if limit and k == fill:
                continue
            if target is not None and ((sign == 1 and h[k] >= target) or (sign == -1 and l[k] <= target)):
                return k, target
        return end, c[end]

    entry = o[t + 1]
    risk = sign * (entry - idea.daily_stop)
    if risk > 0:
        k, px = run(t + 1, entry, idea.daily_stop, None, False)
        r = (sign * (px - entry) - cost) / risk - swap_r(name, idea.seite, entry, risk, x.index[t + 1], x.index[k])
        out["D"] = (r, x.index[t + 1], x.index[k])
    else:
        out["D"] = None
    rng = h[t] - l[t]
    wk = x[["High", "Low"]].resample("W-FRI").agg({"High": "max", "Low": "min"})
    prev_w = wk[wk.index < x.index[t + 1] - pd.Timedelta(days=x.index[t + 1].dayofweek)]
    wh, wl = (prev_w["High"].iat[-1], prev_w["Low"].iat[-1]) if len(prev_w) else (np.nan, np.nan)
    for p, levels in PRICE.items():
        for sk in STOPS:
            for xk in EXITS:
                legs = []
                for lv in levels:
                    if isinstance(lv, tuple):
                        hi, lo, f = wh, wl, lv[1]
                    else:
                        hi, lo, f = h[t], l[t], lv
                    lim = hi - f * (hi - lo) if sign == 1 else lo + f * (hi - lo)
                    if not np.isfinite(lim) or sign * (entry - lim) <= 0:
                        legs.append(None)
                        continue
                    stop = leg_stop(sk, sign, lim, idea.daily_stop, idea.atr)
                    if stop is None:
                        legs.append(None)
                        continue
                    fk = next((k for k in range(t + 1, end + 1)
                               if (sign == 1 and l[k] <= lim) or (sign == -1 and h[k] >= lim)), None)
                    if fk is None:
                        legs.append(("nofill",))
                        continue
                    px_in = min(o[fk], lim) if sign == 1 else max(o[fk], lim)
                    rk = sign * (px_in - stop)
                    if rk <= 0:
                        legs.append(None)
                        continue
                    tg = day_target(x, fk + 1 if fk + 1 <= end else fk, sign, px_in, rk, idea.frac_lvls) if xk == "XB" else None
                    k, px = run(fk, px_in, stop, tg, True)
                    r = (sign * (px - px_in) - cost) / rk - swap_r(name, idea.seite, px_in, rk, x.index[fk], x.index[k])
                    legs.append((r, x.index[fk], x.index[k]))
                out[(p, sk, xk)] = legs
    return out


# --------------------------------------------------------------------------- LTF-Ebene
def ctnl_events(d15: pd.DataFrame) -> dict:
    """H1-Doppel-BOS (Level = ERL zum ersten BOS der Serie), dann M15 Sweep-and-Reject dieses Levels (24 H1-Kerzen)."""
    h1 = d15.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    s = compute_market_structure(h1.rename(columns=str.lower), k=2)
    bias, choch, bos = s["bias"].to_numpy(), s["is_choch"].to_numpy(), s["is_bos"].to_numpy()
    el, eh = s["erl_low"].to_numpy(), s["erl_high"].to_numpy()
    lvl_lo, lvl_hi, cnt, cur_lo, cur_hi = np.full(len(s), np.nan), np.full(len(s), np.nan), 0, np.nan, np.nan
    armed = []
    for i in range(len(s)):
        if choch[i]:
            cnt, cur_lo, cur_hi = 1, el[i], eh[i]
        elif bos[i]:
            cnt += 1
        if cnt == 2 and (choch[i] or bos[i]):
            armed.append((h1.index[i] + pd.Timedelta(hours=1), "long" if bias[i] == 1 else "short",
                          cur_lo if bias[i] == 1 else cur_hi))
    lo, hi, cl = d15["Low"].to_numpy(), d15["High"].to_numpy(), d15["Close"].to_numpy()
    ev = {"long": [], "short": []}
    for t0, side, lvl in armed:
        if not np.isfinite(lvl):
            continue
        a = d15.index.searchsorted(t0)
        b = d15.index.searchsorted(t0 + pd.Timedelta(hours=24))
        if side == "long":
            k = np.flatnonzero((lo[a:b] < lvl) & (cl[a:b] > lvl))
        else:
            k = np.flatnonzero((hi[a:b] > lvl) & (cl[a:b] < lvl))
        if len(k):
            i = a + int(k[0])
            ev[side].append((i, cl[i], lo[i] if side == "long" else hi[i], False))
    return {k: np.array(v, dtype=float).reshape(-1, 4) for k, v in ev.items()}


def m5_events(name: str, d5: pd.DataFrame) -> dict:
    h1 = d5.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    s = compute_market_structure(h1.rename(columns=str.lower), k=2)
    pl, ph = s["erl_low"].shift(1).to_numpy(), s["erl_high"].shift(1).to_numpy()
    sw_lo = (s["low"].to_numpy() < pl) & (s["close"].to_numpy() >= pl)
    sw_hi = (s["high"].to_numpy() > ph) & (s["close"].to_numpy() <= ph)
    m = compute_market_structure(d5.rename(columns=str.lower), k=2)
    bias, choch, cl = m["bias"].to_numpy(), m["is_choch"].to_numpy(), m["close"].to_numpy()
    lo, hi = m["low"].to_numpy(), m["high"].to_numpy()
    ev = {"long": [], "short": []}
    for side, sw, b in (("long", sw_lo, 1), ("short", sw_hi, -1)):
        for i in np.flatnonzero(sw):
            t0 = h1.index[i] + pd.Timedelta(hours=1)
            a = d5.index.searchsorted(t0)
            k = np.flatnonzero(choch[a:a + M5_CHOCH_BARS] & (bias[a:a + M5_CHOCH_BARS] == b))
            if len(k):
                j = a + int(k[0])
                stop = h1["Low"].iat[i] if b == 1 else h1["High"].iat[i]
                ev[side].append((j, cl[j], stop, False))
    return {k: np.array(v, dtype=float).reshape(-1, 4) for k, v in ev.items()}


def load_m5(name: str) -> pd.DataFrame | None:
    files = M5_FILES.get(name, [f"{name}_M5_2016-01-01_2026-10-28.parquet"])
    try:
        d = pd.concat(pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]] for f in files)
    except FileNotFoundError:
        return None
    d = d[~d.index.duplicated(keep="last")].sort_index()
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    return d.loc[:RUN_END.tz_localize("UTC")]


def ltf_legs(x, ideas_m, name, cost, series: dict) -> dict:
    """{(idea_idx, typ, attempts, stop, exit): [legs]} fuer LTF-Typen."""
    out = {}
    for typ, (d, ev) in series.items():
        if d is None:
            continue
        idx = d.index
        dh, dl, dc = d["High"].to_numpy(), d["Low"].to_numpy(), d["Close"].to_numpy()
        dkey = idx.tz_localize(None).normalize()
        for ii, idea in ideas_m.iterrows():
            sign = 1 if idea.seite == "long" else -1
            a = idx.searchsorted(pd.Timestamp(idea.start).tz_localize("UTC"))
            b = idx.searchsorted(pd.Timestamp(idea.ende).tz_localize("UTC")) - 1
            arr = ev.get(idea.seite, np.empty((0, 4)))
            cand = arr[(arr[:, 0] >= a) & (arr[:, 0] <= b)] if len(arr) else arr
            for att in (1, 3):
                for sk in STOPS:
                    for xk in EXITS:
                        legs, busy = [], -1
                        for i0, entry, _, lim in cand:
                            if len(legs) >= att:
                                break
                            i0, lim = int(i0), bool(lim)
                            if i0 <= busy:
                                continue
                            if lim:
                                w = dl[i0 + 1:min(b, i0 + 20) + 1] <= entry if sign == 1 else dh[i0 + 1:min(b, i0 + 20) + 1] >= entry
                                k = np.flatnonzero(w)
                                if not len(k):
                                    continue
                                i0 = i0 + 1 + int(k[0])
                                if i0 <= busy:
                                    continue
                            stop = leg_stop(sk, sign, entry, idea.daily_stop, idea.atr)
                            if stop is None:
                                continue
                            rk = sign * (entry - stop)
                            tg = None
                            if xk == "XB":
                                kd = x.index.searchsorted(dkey[i0])
                                tg = day_target(x, max(1, min(kd, len(x) - 1)), sign, entry, rk, idea.frac_lvls)
                            ex_i, ex_px = sim_one(dh, dl, dc, i0, entry, stop, tg, b, sign, lim)
                            r = (sign * (ex_px - entry) - cost) / rk - swap_r(name, idea.seite, entry, rk, dkey[i0], dkey[ex_i])
                            legs.append((r, dkey[i0], dkey[ex_i]))
                            busy = ex_i
                        out[(ii, f"{typ} x{att}", sk, xk)] = legs
    return out


# --------------------------------------------------------------------------- Zusammensetzen
def combine(ideas: pd.DataFrame, dl: dict, ll: dict) -> pd.DataFrame:
    rows = []
    for ii, idea in ideas.iterrows():
        D = dl[ii].get("D") if ii in dl else None
        if D is None:
            continue
        for ent in ENTRIES:
            for sk in STOPS:
                for xk in EXITS:
                    if ent in PRICE:
                        legs = dl[ii].get((ent, sk, xk), [])
                        planned = len(PRICE[ent])
                    else:
                        legs = ll.get((ii, ent, sk, xk), [])
                        planned = int(ent[-1])
                    filled = [g for g in legs if g is not None and len(g) == 3]
                    for rk in RISKS:
                        w_d = 1 / (1 + planned) if rk == "RA" else 1.0
                        w_l = 1 / (1 + planned) if rk == "RA" else 1.0
                        units = w_d * D[0] + sum(w_l * g[0] for g in filled)
                        ex = max([D[2]] + [g[2] for g in filled])
                        rows.append({"variante": f"{ent} {sk} {xk} {rk}", "markt": idea.markt, "datum": D[1],
                                     "exit_datum": ex, "r": units, "n_limits": len(filled),
                                     "limit_r": np.mean([g[0] for g in filled]) if filled else np.nan,
                                     "periode": "IS" if D[1] <= pd.Timestamp(IS_END) else "OOS"})
    return pd.DataFrame(rows)


def main() -> None:
    lock = Lock(LOCK)
    lock.register_split("2016-01-01", IS_END, "2025-12-31", "2026-07-28")
    n_var = len(ENTRIES) * len(STOPS) * len(EXITS) * len(RISKS)
    if lock.trials == 0:
        lock.log_trials(n_var, "Twin-Trade: 19 Einstiege x 3 Stops x 2 Ausstiege x 2 Risiko (11.11.)")
    ideas = daily_ideas()
    print(f"Ideen: {len(ideas)}", flush=True)
    dl, ll = {}, {}
    for name, (_, grid, cost) in MARKETS.items():
        im = ideas[ideas["markt"] == name]
        if im.empty:
            continue
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):RUN_END.normalize()], grid)
        for ii, idea in im.iterrows():
            t = int(x.index.searchsorted(idea.signal))
            if t + 1 < len(x):
                dl[ii] = daily_legs(x, idea, t, cost)
        series = {}
        d15 = load_ltf(name, "M15")
        if d15 is not None:
            ev, _ = trigger_events(d15, crt.resample_server(d15, "H1"))
            for typ in ("L1", "L2", "L3", "L5"):
                series[typ] = (d15, {s: ev[(typ, s)] for s in ("long", "short")})
            series["C"] = (d15, ctnl_events(d15))
        d5 = load_m5(name)
        if d5 is not None:
            series["M"] = (d5, m5_events(name, d5))
        ll.update(ltf_legs(x, im, name, cost, series))
        print(f"  {name}: fertig ({', '.join(series)})", flush=True)
    t = combine(ideas, dl, ll)
    t.to_csv("htf_daily_trade/twin_trade_ideen.csv", index=False)
    report(t, lock.trials)


def report(t: pd.DataFrame, n_trials: int) -> None:
    rows = []
    for v, g in t.groupby("variante"):
        row = {"variante": v}
        for per in ("IS", "OOS"):
            st = stats(g.loc[g["periode"] == per, "r"])
            row.update({f"{per}_n": st.get("n"), f"{per}_mean": st.get("mean_r"), f"{per}_t": st.get("t")})
        row["fuellquote"] = (g["n_limits"] > 0).mean()
        row["limit_r"] = g["limit_r"].mean()
        k = konto(g[["datum", "exit_datum", "r"]], lambda x: 0.01)
        row.update({"cagr": k["cagr"], "dd": k["max_dd"]})
        rows.append(row)
    res = pd.DataFrame(rows)
    res["dsr"] = [deflated_sharpe(r.IS_t / np.sqrt(r.IS_n), int(r.IS_n), n_trials) for r in res.itertuples()]
    res = res.sort_values("IS_t", ascending=False)
    res.to_csv("htf_daily_trade/twin_trade_varianten.csv", index=False)
    d_only = t[t["variante"] == f"{ENTRIES[0]} SA XA RB"].copy()
    base = d_only.assign(r=d_only["r"] - d_only["limit_r"].fillna(0) * d_only["n_limits"])
    pd.set_option("display.width", 240)
    kb = konto(base[["datum", "exit_datum", "r"]], lambda x: 0.01)
    print(f"\nDaily allein (EO): IS {base.loc[base.periode == 'IS', 'r'].mean():+.3f} R, OOS "
          f"{base.loc[base.periode == 'OOS', 'r'].mean():+.3f} R, n {len(base)}; Konto 1 %: CAGR {kb['cagr']:+.1%}, DD {kb['max_dd']:.1%}")
    print(f"\n== Top 25 nach IS-t (von {len(res)}), Lock {n_trials} Versuche; r = Einheiten von 1 % ==")
    print(res.head(25).round(3).to_string(index=False))
    parts = res["variante"].str.rsplit(n=3, expand=True)
    for i, dim in enumerate(("Einstieg", "Stop", "Ausstieg", "Risiko")):
        g = res.groupby(parts[i])[["IS_mean", "OOS_mean", "cagr", "dd", "limit_r"]].mean()
        print(f"\nØ je {dim}:\n{g.round(3).to_string()}")


if __name__ == "__main__":
    main()
