"""Daily-Edge (C2 + Typ R) x neue Filter x Einstiege -- IS-Pruefung (Nutzerauftrag 27.11.2026, Plan freigegeben).

    python -m htf_daily_trade.daily_neu_is

Auswahl NUR auf IS 2016-21. OOS 2022-24 und 2025/26 sind bereits gesehen (Lock htf_daily_filter_matrix: OOS, Blind,
Tresor geoeffnet) und stehen nur als Info daneben; Bestaetigung nur im Forward. Lock `htf_daily_neu`.

Ideen (Signale unveraendert):
  C2  backtest_macro.c_signals Typ C2 mit den eingefrorenen Filtern (Faber 10M gegen, COT-Fluss mit, Rohstoff-Veto),
      Stand Schluss Signaltag t, Einstieg ab t+1. Ausstieg 10 Handelstage nach Fuellung (T8).
  R   backtest_r.signals (Fractal-Tief/-Hoch nach RSI-ML-Extrem), bestaetigt am Schluss i+2, Einstieg ab i+3.
      Ausstieg gegenlaeufiges Fractal (T7, max. 30 Tage).
  Ideen-Fenster: Start bis Signaltag + 10 Handelstage.
Einstiege:
  EO   Markt zur Eroeffnung des Starttags, Strukturstop
  EL   eingefroren: C2 Limit 50 % Ausloese-Schluss<->Strukturstop, R Limit 50 % der Fractal-Kerze; 3 Tage, Strukturstop
  W50  Limit Mitte der Vorwochen-Range bis Ideen-Ende, Stop Struktur +/- 0,5 Daily-ATR
  F50  Limit 0,5-Fib der Signalkerze (C2: t, R: i+2), 3 Tage, Stop Signalkerzen-Extrem +/- 0,25 ATR
  M15  Nutzerregel 27.11.: im Ideen-Fenster CHoCH in Ideen-Richtung, dann BOS1, BOS2 (je ein neues Struktur-Level,
       Struktur k=2). Limit am Swing, aus dem der BOS2-Schenkel startete (= letztes bestaetigtes Gegen-Swing beim
       BOS2), 3 Tage gueltig. Stops SA Umkehr-Extrem seit CHoCH-Ursprung | SB Limit-Swing -/+ 1 ATR14(M15) |
       SC Limit-Swing -/+ 0,25 Daily-ATR. Ziele 2R | 3R | ZT Ideen-Ende. NZDUSD auf H1 (keine M15-Datei).
Filter (Stand Schluss Signaltag, ohne Vorgriff):
  F0 keiner | F1 RSI-MA-Cross in Trade-Richtung (3 Kerzen) | F2 ML-Flaeche >= 50 % passend zur Seite (3 Kerzen)
  F3 Makro-Veto: FX >= 5 von M1/M2/M3/M6/M7/X3/X4 gegen, Gold-Makro-Veto gegen | F4 Fuelltag kein News-Tag
  F5 DXY 20 Tage mit (X2) | F6 Carry-Veto (M2 gegen faellt weg)
Danach je Basis 2 Paare aus den 3 besten Einzelfiltern (IS).
Kosten Spread+Kommission (filter_matrix.MARKETS) + TTP-Swap (twin_trade.swap_r). Stop vor Ziel; in der Fuellkerze
eines Limits nur der Stop. Je Markt und Seite ein Trade zur Zeit (gefilterte Ideen sperren nicht).
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd

from fusion_lab.filters.cot_flow import CotFlowFilter
from gold_smc_htf_ltf.structure import compute_market_structure
from htf_daily_trade import indikator_edge as ie
from htf_daily_trade.backtest_macro import c_signals
from htf_daily_trade.backtest_r import features, signals, stats
from htf_daily_trade.backtest_varianten import simulate
from htf_daily_trade.c2_veto_combos import commodity_state
from htf_daily_trade.filter_matrix import MARKETS, METALS, USD_ORIENT, MacroDirs, closes, load_market, trend_dirs
from htf_daily_trade.ltf_entry import LTF_FILES, METAL_FILES, MIN_STOP_ATR
from htf_daily_trade.twin_trade import swap_r
from research_lock import Lock, deflated_sharpe

LOCK = "htf_daily_neu"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2021-12-31", "2024-12-31", "2026-11-25"
WARMUP = "2014-01-01"
IDEA_DAYS, LIMIT_DAYS = 10, 3
DAILY = ("EO", "EL", "W50", "F50")
M15 = [f"M15 {s} {z}" for s in ("SA", "SB", "SC") for z in ("2R", "3R", "ZT")]
ENTRIES = list(DAILY) + M15
FILTERS = ("F0", "F1", "F2", "F3", "F4", "F5", "F6")
FX_MACRO = ("M1", "M2", "M3", "M6", "M7", "X3", "X4")
EXIT = {"C2": "T8", "R": "T7"}


# --------------------------------------------------------------------------- Ideen
def ideas_market(name: str, x: pd.DataFrame, cot: CotFlowFilter) -> list[dict]:
    td = trend_dirs(x)
    o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    n = len(x)
    out = []
    for s in c_signals(x):
        if s["kind"] != "C2" or s["i"] + 1 >= n:
            continue
        t, sign = s["i"], 1 if s["side"] == "long" else -1
        if td["T6"].iat[t] * sign >= 0 or cot.direction(name, x.index[t + 1]) * sign <= 0:
            continue
        out.append(dict(base="C2", markt=name, side=s["side"], sign=sign, sig=t, start=t + 1, struct=s["frac_lvl"],
                        atr=s["atr"], el=(c[t] + s["frac_lvl"]) / 2, sc=t))
    for s in signals(x):
        if s["etype"] != "E2":
            continue
        i, sign = s["i"], 1 if s["side"] == "long" else -1
        out.append(dict(base="R", markt=name, side=s["side"], sign=sign, sig=i + 2, start=i + 3, struct=s["frac_lvl"],
                        atr=s["atr"], el=(h[i] + l[i]) / 2, sc=i + 2))
    for d in out:
        d["end"] = min(n - 1, d["sig"] + IDEA_DAYS)
        d["datum"] = x.index[d["start"]]
    return out


def add_filters(ideas: pd.DataFrame, states: dict, md: MacroDirs) -> pd.DataFrame:
    """Richtungen je Idee, Stand Schluss Signaltag (Index = Signaltag; Makro mit 'vor Starttag')."""
    from fusion_lab.filters.gold_macro_veto import GoldMacroVetoFilter
    gv = GoldMacroVetoFilter()
    rows = []
    for r in ideas.itertuples():
        st = states[r.markt].loc[r.sigdate]
        mac = md.dirs(r.markt, r.datum)
        ex = md.extra(r.markt, r.datum)
        mac.update({"X3": ex["X3"], "X4": ex["X4"]})
        gegen = sum(int(np.sign(mac[f] or 0)) * r.sign < 0 for f in FX_MACRO)
        if r.markt == "XAUUSD":
            try:
                veto = gv.direction(r.datum) * r.sign < 0
            except Exception:
                veto = False
        elif r.markt == "XAGUSD":
            veto = False
        else:
            veto = gegen >= 5
        rows.append({"F1": st["I2"] * r.sign > 0, "F2": st["I4"] * r.sign > 0, "F3": not veto,
                     "F5": st["X2"] * r.sign > 0, "F6": int(np.sign(mac["M2"] or 0)) * r.sign >= 0,
                     "makro_gegen": gegen})
    return pd.concat([ideas.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def dxy_dir(name: str, index: pd.DatetimeIndex) -> pd.Series:
    cl = {k: v.reindex(index).ffill() for k, v in closes().items()}
    ldxy = (-0.576 * np.log(cl["EURUSD"]) + 0.136 * np.log(cl["USDJPY"]) - 0.119 * np.log(cl["GBPUSD"])
            + 0.091 * np.log(cl["USDCAD"]) + 0.036 * np.log(cl["USDCHF"]))
    return (np.sign(ldxy.diff(20)).fillna(0) * USD_ORIENT[name]).astype(int)


# --------------------------------------------------------------------------- Daily-Einstiege
def daily_entries(x: pd.DataFrame, idea: dict, cost: float) -> dict:
    """{einstieg: (r_ohne_swap, r, fuell_k, exit_k) | None}."""
    o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    sign, end_idx = idea["sign"], len(x) - 1
    name = idea["markt"]
    wk = x[["High", "Low"]].resample("W-FRI").agg({"High": "max", "Low": "min"})
    d0 = x.index[idea["start"]]
    prev_w = wk[wk.index < d0 - pd.Timedelta(days=d0.dayofweek)]
    wh, wl = (prev_w["High"].iat[-1], prev_w["Low"].iat[-1]) if len(prev_w) else (np.nan, np.nan)
    sc = idea["sc"]
    rng = h[sc] - l[sc]
    plan = {
        "EO": (None, idea["struct"], 0),
        "EL": (idea["el"], idea["struct"], LIMIT_DAYS),
        "W50": ((wh + wl) / 2, idea["struct"] - sign * 0.5 * idea["atr"], idea["end"] - idea["start"] + 1),
        "F50": (h[sc] - 0.5 * rng if sign == 1 else l[sc] + 0.5 * rng,
                (l[sc] if sign == 1 else h[sc]) - sign * 0.25 * idea["atr"], LIMIT_DAYS),
    }
    out = {}
    for e, (lvl, stop, days) in plan.items():
        out[e] = None
        s0 = idea["start"]
        if s0 > end_idx:
            continue
        if lvl is None:
            k, px, lim = s0, o[s0], False
        else:
            # W50 wie c2_ladder: Limit muss beim Signal auf der guenstigen Seite liegen; EL/F50 wie das Original
            # (liegt der Kurs schon jenseits, Fuellung zur Eroeffnung)
            if not np.isfinite(lvl) or (e == "W50" and sign * (c[idea["sig"]] - lvl) <= 0):
                continue
            k = next((k for k in range(s0, min(end_idx, s0 + days - 1) + 1)
                      if (sign == 1 and l[k] <= lvl) or (sign == -1 and h[k] >= lvl)), None)
            if k is None:
                continue
            px, lim = (min(o[k], lvl) if sign == 1 else max(o[k], lvl)), True
        risk = sign * (px - stop)
        if not (risk > 0):
            continue
        en = dict(side=idea["side"], fill=k, price=px, struct=stop, atr=idea["atr"], start=k, limit=lim)
        res = simulate(x, en, "S1", EXIT[idea["base"]], cost, end_idx)
        if res is None:
            continue
        sw = swap_r(name, idea["side"], px, risk, x.index[k], x.index[res["exit_k"]])
        out[e] = (res["r"], res["r"] - sw, k, res["exit_k"])
    return out


# --------------------------------------------------------------------------- M15 CHoCH + 2 BOS
def load_m15(name: str) -> pd.DataFrame:
    files = METAL_FILES["M15"].get(name) or [LTF_FILES["M15"].format(m=name)]
    try:
        parts = [pd.read_parquet(f"data_cache/combined/{f}")[["Open", "High", "Low", "Close"]] for f in files]
    except FileNotFoundError:
        parts = [pd.read_parquet(f"data_cache/combined/{LTF_FILES['H1'].format(m=name)}")[["Open", "High", "Low", "Close"]]]
    d = pd.concat(parts).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    if d.index.tz is not None:
        d.index = d.index.tz_convert("UTC").tz_localize(None)
    return d.loc["2015-06-01":]


def struct_events(d: pd.DataFrame) -> dict:
    """Kausale Struktur: CHoCH-Flag, Bruch eines NEUEN Levels je Richtung, Pivot-Index der Levels."""
    s = compute_market_structure(d.rename(columns=str.lower), k=2)
    n = len(s)
    hi, lo = s["erl_high"].to_numpy(), s["erl_low"].to_numpy()
    c = s["close"].to_numpy()
    shc, slc = s["swing_high_confirmed"].to_numpy(), s["swing_low_confirmed"].to_numpy()
    piv_hi, piv_lo = np.full(n, -1), np.full(n, -1)
    ph = pl = -1
    up, dn = np.zeros(n, bool), np.zeros(n, bool)
    last_up = last_dn = np.nan
    for i in range(n):
        if shc[i]:
            ph = i - 2
        if slc[i]:
            pl = i - 2
        piv_hi[i], piv_lo[i] = ph, pl
        if c[i] > hi[i] and hi[i] != last_up:
            up[i], last_up = True, hi[i]
        if c[i] < lo[i] and lo[i] != last_dn:
            dn[i], last_dn = True, lo[i]
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - d["Close"].shift()).abs(),
                    (d["Low"] - d["Close"].shift()).abs()], axis=1).max(axis=1)
    return {"choch": s["is_choch"].to_numpy(), "bias": s["bias"].to_numpy(), "up": up, "dn": dn,
            "erl_hi": hi, "erl_lo": lo, "piv_hi": piv_hi, "piv_lo": piv_lo,
            "atr": tr.rolling(14).mean().to_numpy(), "t": d.index}


def bos2_setup(ev: dict, h, l, c, i0: int, i1: int, sign: int):
    """Erste Folge CHoCH -> BOS1 -> BOS2 in Ideen-Richtung zwischen i0 und i1. -> (bos2_i, limit, umkehr_extrem)."""
    cnt, rev_from = None, -1
    brk = ev["up"] if sign == 1 else ev["dn"]
    for i in range(i0, i1):
        if ev["choch"][i]:
            if ev["bias"][i] == sign:
                cnt = 0
                rev_from = ev["piv_hi"][i] if sign == 1 else ev["piv_lo"][i]   # Ursprung des gebrochenen Levels
            else:
                cnt = None
            continue
        if cnt is not None and brk[i]:
            cnt += 1
            if cnt == 2:
                lim = ev["erl_lo"][i] if sign == 1 else ev["erl_hi"][i]
                if not np.isfinite(lim) or sign * (c[i] - lim) <= 0 or rev_from < 0:
                    return None
                ext = l[rev_from:i + 1].min() if sign == 1 else h[rev_from:i + 1].max()
                return i, lim, ext
    return None


def m15_entries(name: str, d: pd.DataFrame, ev: dict, idea: dict, x: pd.DataFrame, cost: float) -> dict:
    o, h, l, c = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    ts = ev["t"]
    sign = idea["sign"]
    t_start = x.index[idea["start"]]
    t_end = x.index[idea["end"]] + pd.Timedelta(days=1)
    i0, i1 = ts.searchsorted(t_start), ts.searchsorted(t_end)
    out = {e: None for e in M15}
    st = bos2_setup(ev, h, l, c, i0, i1, sign)
    if st is None:
        return out
    b, lim, ext = st
    f_end = min(i1, ts.searchsorted(ts[b] + pd.Timedelta(days=LIMIT_DAYS)))
    f = next((k for k in range(b + 1, f_end) if (sign == 1 and l[k] <= lim) or (sign == -1 and h[k] >= lim)), None)
    if f is None:
        return out
    px = min(o[f], lim) if sign == 1 else max(o[f], lim)
    stops = {"SA": ext, "SB": lim - sign * ev["atr"][b], "SC": lim - sign * 0.25 * idea["atr"]}
    for sk, stop in stops.items():
        if not np.isfinite(stop):
            continue
        # Mindeststop 0,1 x Daily-ATR wie ltf_entry (MIN_STOP_ATR), sonst winzige Risiken -> R-Ausreisser
        if sign * (px - stop) < MIN_STOP_ATR * idea["atr"]:
            stop = px - sign * MIN_STOP_ATR * idea["atr"]
        risk = sign * (px - stop)
        if not (risk > 0):
            continue
        for z in ("2R", "3R", "ZT"):
            tgt = None if z == "ZT" else px + sign * int(z[0]) * risk
            ex, j = None, i1 - 1
            for k in range(f, i1):
                if (sign == 1 and l[k] <= stop) or (sign == -1 and h[k] >= stop):
                    ex, j = stop, k
                    break
                if k > f and tgt is not None and ((sign == 1 and h[k] >= tgt) or (sign == -1 and l[k] <= tgt)):
                    ex, j = tgt, k
                    break
            if ex is None:
                ex = c[j]
            r0 = (sign * (ex - px) - cost) / risk
            sw = swap_r(name, idea["side"], px, risk, ts[f], ts[j])
            kf = min(x.index.searchsorted(ts[f].normalize(), side="right") - 1, len(x) - 1)
            kx = min(x.index.searchsorted(ts[j].normalize(), side="right") - 1, len(x) - 1)
            out[f"M15 {sk} {z}"] = (r0, r0 - sw, kf, kx)
    return out


# --------------------------------------------------------------------------- Auswertung
def build() -> pd.DataFrame:
    """Je Idee x Einstieg ein Ergebnis (ohne Sperrlogik)."""
    cot = CotFlowFilter(4)
    md = MacroDirs()
    md.init_extra()
    rows, states = [], {}
    for name, (_, grid, cost) in MARKETS.items():
        x = features(load_market(name).loc[pd.Timestamp(WARMUP):], grid)
        st = ie.states(x.rename(columns=str.lower))[["I2", "I4"]]
        st["X2"] = dxy_dir(name, x.index)
        states[name] = st
        d15 = load_m15(name)
        ev = struct_events(d15)
        n_id = 0
        for idea in ideas_market(name, x, cot):
            if x.index[idea["start"]] < pd.Timestamp(IS_START):
                continue
            res = daily_entries(x, idea, cost)
            if d15.index[-1] > x.index[idea["end"]]:
                res.update(m15_entries(name, d15, ev, idea, x, cost))
            for e, v in res.items():
                if v is None:
                    continue
                rows.append({"base": idea["base"], "markt": name, "side": idea["side"], "sign": idea["sign"],
                             "sigdate": x.index[idea["sig"]], "datum": idea["datum"], "einstieg": e,
                             "fill": x.index[v[2]], "exit": x.index[v[3]], "fill_k": v[2], "exit_k": v[3],
                             "r_ohne_swap": v[0], "r": v[1]})
            n_id += 1
        print(f"  {name}: {n_id} Ideen", flush=True)
    t = pd.DataFrame(rows)
    ideas = t.drop_duplicates(["base", "markt", "side", "sigdate"])[["base", "markt", "side", "sign", "sigdate", "datum"]]
    ideas = add_filters(ideas, states, md)
    # Rohstoff-Veto (eingefroren) nur fuer C2
    ideas["RS"] = commodity_state(ideas.rename(columns={"side": "seite"}), start="2014-01-01", end="2026-11-30")
    t = t.merge(ideas.drop(columns=["sign", "datum"]), on=["base", "markt", "side", "sigdate"])
    t = t[~((t["base"] == "C2") & (t["RS"] == "gegen"))].copy()
    t["F4"] = ~t["fill"].dt.normalize().isin(md.news)
    t["F0"] = True
    t["periode"] = np.select([t["fill"] <= pd.Timestamp(IS_END), t["fill"] <= pd.Timestamp(OOS_END)],
                             ["IS", "OOS"], "2025+")
    return t


def cell_trades(t: pd.DataFrame, base: str, entry: str, filt: tuple) -> pd.DataFrame:
    s = t[(t["base"] == base) & (t["einstieg"] == entry)]
    for f in filt:
        s = s[s[f]]
    keep, busy = [], {}
    for r in s.sort_values("fill_k").itertuples():
        key = (r.markt, r.side)
        if r.fill_k <= busy.get(key, -1):
            continue
        busy[key] = r.exit_k
        keep.append(r.Index)
    return s.loc[keep]


def summary(g: pd.DataFrame, n_trials: int) -> dict:
    row = {}
    for per in ("IS", "OOS", "2025+"):
        p = g[g["periode"] == per]
        st = stats(p["r"]) if len(p) > 1 else {"n": len(p)}
        row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan)})
    i = g[g["periode"] == "IS"]
    top = i["r"].sort_values(ascending=False)
    row["IS_ohne_top3"] = top.iloc[3:].mean() if len(top) > 3 else np.nan
    row["IS_ohne_swap"] = i["r_ohne_swap"].mean()
    row["maerkte+"] = int((i.groupby("markt")["r"].mean() > 0).sum())
    row["jahre+"] = int((i.groupby(i["fill"].dt.year)["r"].mean() > 0).sum())
    row["dsr"] = deflated_sharpe(i["r"].mean() / i["r"].std(ddof=1), len(i), n_trials) if len(i) > 2 else np.nan
    row["kriterium"] = bool(row["IS_t"] > 2 and row["IS_n"] >= 40 and row["IS_ohne_top3"] > 0 and row["maerkte+"] >= 6)
    return row


def main() -> None:
    pd.set_option("display.width", 240)
    lock = Lock(LOCK)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    n1 = 2 * len(ENTRIES) * len(FILTERS)
    if lock.trials == 0:
        lock.log_trials(n1, "C2/R x 13 Einstiege x F0-F6 einzeln (27.11.); OOS 2022-24 + 2025/26 schon gesehen "
                            "(Lock htf_daily_filter_matrix), nur Info")
    t = build()
    t.to_parquet("htf_daily_trade/daily_neu_trades.parquet")
    rows = []
    for base, e, f in itertools.product(("C2", "R"), ENTRIES, FILTERS):
        rows.append({"base": base, "einstieg": e, "filter": f, **summary(cell_trades(t, base, e, (f,)), lock.trials)})
    res = pd.DataFrame(rows)
    # Paare: 3 beste Einzelfilter je Basis nach mittlerem IS-Zuwachs gegen F0 ueber alle Einstiege
    f0 = res[res["filter"] == "F0"].set_index(["base", "einstieg"])["IS_R"]
    res["IS_delta"] = res["IS_R"] - res.set_index(["base", "einstieg"]).index.map(f0)
    pairs = {}
    for base in ("C2", "R"):
        best = (res[(res["base"] == base) & (res["filter"] != "F0")].groupby("filter")["IS_delta"].mean()
                .sort_values(ascending=False).index[:3].tolist())
        pairs[base] = [(best[0], best[1]), (best[0], best[2])]
    if not any(f"Paare je Basis aus 3 besten Einzelfiltern: {pairs}" in str(ev.get("note")) for ev in _events(lock)):
        lock.log_trials(2 * 2 * len(ENTRIES), f"Paare je Basis aus 3 besten Einzelfiltern: {pairs} (27.11.)")
    for base, pp in pairs.items():
        for p in pp:
            for e in ENTRIES:
                rows.append({"base": base, "einstieg": e, "filter": "+".join(p),
                             **summary(cell_trades(t, base, e, p), lock.trials)})
    res = pd.DataFrame(rows)
    res["IS_delta"] = res["IS_R"] - res.set_index(["base", "einstieg"]).index.map(f0)
    res.to_csv("htf_daily_trade/daily_neu_is.csv", index=False)
    cols = ["base", "einstieg", "filter", "IS_n", "IS_R", "IS_t", "IS_ohne_top3", "maerkte+", "jahre+", "dsr",
            "kriterium", "OOS_n", "OOS_R", "2025+_n", "2025+_R"]
    for base in ("C2", "R"):
        b = res[res["base"] == base]
        print(f"\n===== {base}: F0 je Einstieg =====")
        print(b[b["filter"] == "F0"][cols].round(3).to_string(index=False))
        print(f"\n===== {base}: Filter-Mittel IS-Zuwachs ueber alle Einstiege =====")
        print(b.groupby("filter")[["IS_delta", "IS_R", "OOS_R", "2025+_R"]].mean().round(3).T.to_string())
        print(f"\n===== {base}: Top 12 nach IS-t (n >= 40) =====")
        print(b[b["IS_n"] >= 40].sort_values("IS_t", ascending=False).head(12)[cols].round(3).to_string(index=False))
    print(f"\nKriterium erfuellt: {int(res['kriterium'].sum())} von {len(res)} | Lock {lock.trials} Versuche | Paare {pairs}")


def _events(lock: Lock) -> list[dict]:
    import json
    if not lock.log_path.exists():
        return []
    return [json.loads(x) for x in lock.log_path.read_text(encoding="utf-8").splitlines() if x.strip()]


def reproduktion() -> None:
    """F0-Pruefung gegen eingefrorene Staende: R EL ohne Swap (filter_matrix R, 9 Maerkte IS +0,29) und C2 EL."""
    t = pd.read_parquet("htf_daily_trade/daily_neu_trades.parquet")
    for base in ("R", "C2"):
        g = cell_trades(t, base, "EL", ("F0",))
        g = g[g["periode"] == "IS"]
        print(f"{base} EL F0 IS: n {len(g)}, ohne Swap {g['r_ohne_swap'].mean():+.3f}, mit Swap {g['r'].mean():+.3f}")
    fm = pd.read_csv("htf_daily_trade/filter_matrix_trades.csv", parse_dates=["datum"])
    r = fm[(fm["setup"] == "R") & (fm["periode"] == "IS")]
    print(f"Referenz filter_matrix R IS: n {len(r)}, {r['r'].mean():+.3f}")
    ref = pd.read_csv("htf_daily_trade/c2_kandidat_trades.csv", parse_dates=["einstieg"])
    ref = ref[ref["einstieg"] <= IS_END]
    print(f"Referenz eingefroren C2 IS: n {len(ref)}, ohne Swap {ref['r_netto_ohne_swap'].mean():+.3f}, "
          f"TTP {ref['r_TTP'].mean():+.3f}")


if __name__ == "__main__":
    reproduktion() if "--repro" in sys.argv else main()
