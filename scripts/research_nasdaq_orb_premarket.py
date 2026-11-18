"""NASDAQ-ORB aus der Vorboersen-Range 09:00-09:30 NY (Nutzerauftrag 15.11.2026, Anlass: ORB-News).

Frage des Nutzers: Breakout aus der Range 09:00-09:30 NY im M5, SL am anderen Range-Ende, Trendfilter
EMA50 vs. EMA200, reale Kosten, NASDAQ. Vergleich mit unserem NASDAQ-ORB in IS und OOS. Ranges, TP und
SL optimieren. Pruefen, ob VIX, Makro, Stress und Regime als Richtungsfilter taugen.

SPLIT (Lock `nasdaq_orb_premarket_20261115`, Overfitting-Sperre Stand 10.11.2026):
  IS     2016-07-28 .. 2022-12-31   optimieren (gleiche IS-Grenze wie der alte ORB-IS-Lauf)
  OOS    2023-01-01 .. 2026-05-14   frei ansehen
  Tresor 2026-05-15 .. 2026-11-14   letzte 6 Monate, bleibt zu

MECHANIK (fest):
  Range = Hoch/Tief der M5-Kerzen im Fenster. Ab Range-Ende Stop-Order an beiden Enden (OCO), Einstieg bis
  11:55 (letzte M5-Kerze vor 12:00). Gap ueber das Level -> Fuellung zum Eroeffnungskurs. Beruehrt eine Kerze
  beide Enden, gilt die Seite naeher am Eroeffnungskurs. Ausstieg SL / TP / 15:55-Kerzenschluss.
  Konservativ: TP zaehlt erst ab der Kerze NACH dem Einstieg, und in der Kerze, in der der SL faellt, zaehlt
  kein TP. Gap ueber den SL -> Fuellung zum Eroeffnungskurs.
  Kosten: Spread 0,54 bps + Slippage 0,45 + 0,30 bps (wie alle ORB-Laeufe), als R-Abzug je Trade.

GITTER (5 optimierte Punkte, unter dem Richtwert 9):
  Range-Beginn 08:00/08:30/09:00/09:15 x Range-Ende 09:30/09:45 (+ 09:30-09:45 als Cash-Referenz)
  SL = Level minus 1,0 / 0,75 / 0,5 Range-Breite (1,0 = anderes Range-Ende)
  TP 1 / 1,5 / 2 / 3 / 4 R / ohne (Tagesschluss)
  Trend EMA50 vs. EMA200: keiner / M5 / H1 / D1 (Stand bei Range-Ende, nur abgeschlossene Kerzen)

AUSWAHLREGEL (vor dem Lauf, nur IS): >= 100 Trades, PF > 1,1, beide IS-Haelften > 0; Score = t-Wert,
geglaettet als Median aus Zelle und SL-/TP-Nachbarn. Gewinner = hoechster Score.

RICHTUNGSFILTER (je Tag nur Vortagswerte):
  VIX-Niveau (>= 20), VIX gegen 20-Tage-Schnitt, Stress (TAIL oder STLFSI > 1), Realzins-Trend 20 Tage,
  Regime (Landi-Karte, Vorzeichen Wachstum x Inflation). Regel auf IS gelernt: je Zustand nur die Seiten
  mit IS-Ø R > 0 (mind. 20 Trades), dann OOS. Je Filter zwei Varianten: allein (statt EMA) und mit EMA.

  python scripts/research_nasdaq_orb_premarket.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ny_open_orb.data import fetch_m5  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "nasdaq_orb_premarket_20261115"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-07-28", "2022-12-31", "2026-05-14", "2026-11-14"
OUT = ROOT / "ny_open_orb" / "results" / "premarket_0900"
COST_BPS = 0.54 + 0.45 + 0.30

RANGES = [(s, e) for s in ("08:00", "08:30", "09:00", "09:15") for e in ("09:30", "09:45")] + [("09:30", "09:45")]
SLS = [1.0, 0.75, 0.5]
TPS = [1.0, 1.5, 2.0, 3.0, 4.0, None]
TRENDS = ["keiner", "M5", "H1", "D1"]
ENTRY_CUTOFF = "11:55"
LAST_BAR = "15:55"
USER_BASE = dict(range=("09:00", "09:30"), sl=1.0, trend="M5")


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


# --------------------------------------------------------------------------- Daten
def load_m5() -> pd.DataFrame:
    df = fetch_m5("NASDAQ", IS_START, TRESOR_END)
    return df[["open", "high", "low", "close"]].astype(float)


def trend_states(m5: pd.DataFrame, days: list, range_end: str) -> dict[str, dict]:
    """+1/-1 je Tag und Zeitebene, nur aus Kerzen, die bei Range-Ende abgeschlossen sind."""
    out = {"keiner": {d: 0 for d in days}}
    c = m5["close"]
    sig = lambda s: np.sign(s.ewm(span=50, adjust=False).mean() - s.ewm(span=200, adjust=False).mean())
    m5s = sig(c)
    h1 = c.resample("1h", label="left", closed="left").last().dropna()
    h1s = sig(h1)
    h1s.index = h1s.index + pd.Timedelta(hours=1)          # Stempel = Zeitpunkt, ab dem die Kerze bekannt ist
    sess = c[(c.index.time <= pd.Timestamp(LAST_BAR).time())]
    d1 = sess.groupby(sess.index.date).last()
    d1.index = pd.to_datetime(d1.index)
    d1s = sig(d1)
    hh, mm = map(int, range_end.split(":"))
    res = {"M5": {}, "H1": {}, "D1": {}}
    for d in days:
        t_end = pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=hh, minutes=mm)
        last_m5 = t_end - pd.Timedelta(minutes=5)           # Kerze mit Stempel t_end-5 schliesst bei t_end
        res["M5"][d] = float(m5s.asof(last_m5)) if last_m5 >= m5s.index[0] else 0.0
        res["H1"][d] = float(h1s.asof(t_end)) if t_end >= h1s.index[0] else 0.0
        prev = d1s[d1s.index < pd.Timestamp(d)]
        res["D1"][d] = float(prev.iloc[-1]) if len(prev) else 0.0
    out.update(res)
    return out


# --------------------------------------------------------------------------- Simulation
def day_arrays(m5: pd.DataFrame) -> dict:
    """Je Handelstag die M5-Kerzen 08:00-15:55 als Arrays."""
    w = m5[(m5.index.time >= pd.Timestamp("08:00").time()) & (m5.index.time <= pd.Timestamp(LAST_BAR).time())]
    w = w[w.index.dayofweek < 5]
    days = {}
    for d, g in w.groupby(w.index.date):
        if len(g) < 80:                                     # Halbtage/Luecken (voll = 96 Kerzen)
            continue
        mins = (g.index.hour * 60 + g.index.minute).to_numpy()
        if mins[-1] != 15 * 60 + 55:
            continue
        days[pd.Timestamp(d)] = dict(m=mins, o=g.open.to_numpy(), h=g.high.to_numpy(), l=g.low.to_numpy(),
                                     c=g.close.to_numpy())
    return days


def hm(s: str) -> int:
    h, m = map(int, s.split(":"))
    return h * 60 + m


def sim_day(a: dict, rs: int, re: int, slf: float, allowed: tuple) -> dict | None:
    m, o, h, l, c = a["m"], a["o"], a["h"], a["l"], a["c"]
    rmask = (m >= rs) & (m < re)
    if rmask.sum() < (re - rs) // 5 - 1:
        return None
    rh, rl = h[rmask].max(), l[rmask].min()
    width = rh - rl
    if width <= 0:
        return None
    cut = hm(ENTRY_CUTOFF)
    e, d = None, 0
    for j in np.where((m >= re) & (m <= cut))[0]:
        up = 1 in allowed and h[j] >= rh
        dn = -1 in allowed and l[j] <= rl
        if up and dn:
            d = 1 if abs(rh - o[j]) <= abs(o[j] - rl) else -1
        elif up:
            d = 1
        elif dn:
            d = -1
        if d:
            e = j
            break
    if e is None:
        return None
    if d == 1:
        p = max(o[e], rh)
        sl = rh - slf * width
    else:
        p = min(o[e], rl)
        sl = rl + slf * width
    risk = abs(p - sl)
    if risk <= 0:
        return None
    # SL in der Einstiegskerze (konservativ: zaehlt)
    if (d == 1 and l[e] <= sl) or (d == -1 and h[e] >= sl):
        return dict(dir=d, entry=p, risk=risk, mfe=0.0, sl_hit=True, sl_r=-1.0, eod_r=np.nan,
                    cost_r=p * COST_BPS / 1e4 / risk, entry_min=int(m[e]))
    k_sl, sl_r = None, -1.0
    for j in range(e + 1, len(m)):
        if (d == 1 and l[j] <= sl) or (d == -1 and h[j] >= sl):
            k_sl = j
            fill = min(o[j], sl) if d == 1 else max(o[j], sl)
            sl_r = (fill - p) * d / risk
            break
    stop = k_sl if k_sl is not None else len(m)
    seg = slice(e + 1, stop)
    mfe = ((h[seg].max() - p) / risk if d == 1 else (p - l[seg].min()) / risk) if stop > e + 1 else 0.0
    return dict(dir=d, entry=p, risk=risk, mfe=mfe, sl_hit=k_sl is not None, sl_r=sl_r,
                eod_r=(c[-1] - p) * d / risk, cost_r=p * COST_BPS / 1e4 / risk, entry_min=int(m[e]))


def r_for_tp(t: pd.DataFrame, tp) -> pd.Series:
    if tp is None:
        gross = np.where(t.sl_hit, t.sl_r, t.eod_r)
    else:
        gross = np.where(t.mfe >= tp, tp, np.where(t.sl_hit, t.sl_r, t.eod_r))
    return pd.Series(gross - t.cost_r.to_numpy(), index=t.index)


def base_trades(days: dict, rng: tuple, slf: float, allowed_by_day) -> pd.DataFrame:
    rs, re = hm(rng[0]), hm(rng[1])
    rows = []
    for d, a in days.items():
        al = allowed_by_day(d)
        if not al:
            continue
        x = sim_day(a, rs, re, slf, al)
        if x:
            x["day"] = d
            rows.append(x)
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t["time"] = [pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(minutes=int(mm))
                 for d, mm in zip(t.day, t.entry_min)]
    return t.set_index("time").sort_index()


def allowed_from_trend(ts: dict, trend: str):
    if trend == "keiner":
        return lambda d: (1, -1)
    return lambda d: ((1,) if ts[trend].get(d, 0) > 0 else (-1,) if ts[trend].get(d, 0) < 0 else ())


# --------------------------------------------------------------------------- Kennzahlen
def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {"n": len(r)}
    std = r.std(ddof=1)
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    half = len(r) // 2
    yrs = max((r.index.max() - r.index.min()).days / 365.25, 0.1)
    return {"n": len(r), "pro_jahr": len(r) / yrs, "avg": r.mean(), "std": std,
            "t": r.mean() / std * np.sqrt(len(r)) if std > 0 else np.nan,
            "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
            "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
            "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "win": (r > 0).mean(),
            "jahre_pos": f"{int((r.groupby(r.index.year).sum() > 0).sum())}/{r.index.year.nunique()}",
            "skew": float(r.skew()), "kurt": float(r.kurt() + 3)}


# --------------------------------------------------------------------------- Filter
def filter_states(days: list) -> dict[str, pd.Series]:
    """Zustand je Handelstag, nur aus Werten bis zum Vortag."""
    idx = pd.DatetimeIndex(days)
    hist = pd.read_parquet(ROOT / "data_cache" / "geo" / "history.parquet")
    hist.index = pd.to_datetime(hist.index).normalize()

    def prior(s: pd.Series) -> pd.Series:
        s = s.dropna()
        s = s[~s.index.duplicated(keep="last")]
        return pd.Series([s[s.index < d].iloc[-1] if (s.index < d).any() else np.nan for d in idx], index=idx)

    vix = hist["vix"].dropna()
    st = {}
    v = prior(vix)
    st["VIX-Niveau"] = pd.Series(np.where(v >= 20, "VIX>=20", "VIX<20"), index=idx).where(v.notna())
    vt = prior(vix - vix.rolling(20).mean())
    st["VIX-Trend"] = pd.Series(np.where(vt > 0, "VIX steigt", "VIX faellt"), index=idx).where(vt.notna())
    rz = prior(hist["real_10y"].dropna().diff(20))
    st["Realzins-Trend"] = pd.Series(np.where(rz > 0, "Realzins steigt", "Realzins faellt"), index=idx).where(rz.notna())
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from scripts.research_macro_scorecard import regime_halves
        half = regime_halves(idx)                              # schon auf den Vortag verschoben
        st["Stress"] = pd.Series(np.where(half < 1.0, "Stress", "ruhig"), index=idx)
    except Exception as exc:  # noqa: BLE001
        print("Stress-Quelle nicht verfuegbar, Ersatz VIX > 28:", exc)
        st["Stress"] = pd.Series(np.where(v > 28, "Stress", "ruhig"), index=idx).where(v.notna())
    lab = pd.read_parquet(ROOT / "fusion_lab" / "data" / "macro_regime" / "labels.parquet")
    lab.index = pd.to_datetime(lab.index).normalize()
    st["Regime"] = prior(lab["signs"])
    return st


def learn_rule(t_is: pd.DataFrame, state: pd.Series, r_is: pd.Series) -> dict:
    """Je Zustand die Seiten mit IS-Ø R > 0 (mind. 20 Trades)."""
    s = t_is["day"].map(state)
    rule = {}
    for z in s.dropna().unique():
        sides = []
        for d in (1, -1):
            m = (s == z) & (t_is["dir"] == d)
            if m.sum() >= 20 and r_is[m].mean() > 0:
                sides.append(d)
        rule[z] = tuple(sides)
    return rule


def state_table(t: pd.DataFrame, r: pd.Series, state: pd.Series, part: str, fname: str) -> list[dict]:
    s = t["day"].map(state)
    rows = []
    for z in sorted(s.dropna().unique()):
        for d, name in ((1, "long"), (-1, "short")):
            m = (s == z) & (t["dir"] == d)
            rows.append({"filter": fname, "teil": part, "zustand": z, "seite": name, "n": int(m.sum()),
                         "avg": r[m].mean() if m.any() else np.nan, "sum": r[m].sum()})
    return rows


# --------------------------------------------------------------------------- Hauptlauf
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lk = lock()
    m5 = load_m5()
    m5 = m5[m5.index < pd.Timestamp(OOS_END, tz="America/New_York") + pd.Timedelta(days=1)]   # Tresor nie geladen
    days = day_arrays(m5)
    day_list = sorted(days)
    print(f"{len(day_list)} Handelstage {day_list[0].date()} .. {day_list[-1].date()}", flush=True)
    ts_by_end = {e: trend_states(m5, day_list, e) for e in sorted({r[1] for r in RANGES})}

    # --- Gitter (alle Zeitraeume gerechnet, Auswahl nur auf IS) -------------
    rows, store = [], {}
    for rng, slf, trend in itertools.product(RANGES, SLS, TRENDS):
        t = base_trades(days, rng, slf, allowed_from_trend(ts_by_end[rng[1]], trend))
        store[(rng, slf, trend)] = t
        for tp in TPS:
            r = r_for_tp(t, tp)
            for part, rr in (("IS", lk.is_only(r)), ("OOS", lk.oos_only(r))):
                mm = metrics(rr)
                rows.append({"range": f"{rng[0]}-{rng[1]}", "sl": slf, "tp": tp if tp else "EOD", "trend": trend,
                             "teil": part, **{k: mm.get(k) for k in ("n", "pro_jahr", "avg", "std", "t", "pf", "sum",
                                                                     "dd", "h1", "h2", "win", "jahre_pos")}})
        print(f"  {rng} SL {slf} {trend}: {len(t)} Trades", flush=True)
    grid = pd.DataFrame(rows)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if st["trials"] == 0:
        lk.log_trials(len(RANGES) * len(SLS) * len(TPS) * len(TRENDS), note="Gitter Range x SL x TP x Trend")
    grid.to_csv(OUT / "grid.csv", index=False)

    # --- Auswahl nur IS ------------------------------------------------------
    gi = grid[grid.teil == "IS"].copy()
    gi["ok"] = (gi.n >= 100) & (gi.pf > 1.1) & (gi.h1 > 0) & (gi.h2 > 0)
    tps_k = [str(x) if x else "EOD" for x in TPS]
    gi["tp_k"] = gi.tp.astype(str)
    look = gi.set_index(["range", "trend", "sl", "tp_k"])["t"].to_dict()

    def smooth(row):
        si, ti = SLS.index(row.sl), tps_k.index(row.tp_k)
        vals = [look.get((row.range, row.trend, SLS[si + a], tps_k[ti + b]))
                for a, b in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= si + a < len(SLS) and 0 <= ti + b < len(tps_k)]
        vals = [v for v in vals if v is not None and not pd.isna(v)]
        return float(np.median(vals)) if vals else np.nan

    el = gi[gi.ok].copy()
    el["t_glatt"] = el.apply(smooth, axis=1)
    el = el.sort_values("t_glatt", ascending=False)
    el.head(25).to_csv(OUT / "is_top25.csv", index=False)
    pd.set_option("display.width", 250)
    print(f"\nIS: {len(el)} von {len(gi)} Zellen erfuellen die Mindestbedingungen")
    print(el.head(12)[["range", "sl", "tp", "trend", "n", "avg", "pf", "t", "t_glatt", "dd", "jahre_pos"]].round(3).to_string(index=False))
    w = el.iloc[0]
    winner = dict(range=tuple(w.range.split("-")), sl=float(w.sl), tp=None if w.tp == "EOD" else float(w.tp), trend=w.trend)

    # --- Vergleichstabelle --------------------------------------------------
    sr_var = float((gi[gi.n >= 30].avg / gi[gi.n >= 30]["std"]).var())
    variants = {}
    ub = store[(USER_BASE["range"], USER_BASE["sl"], USER_BASE["trend"])]
    for tp in (None, 2.0, 1.0):
        variants[f"Nutzer-Basis 09:00-09:30, SL Range, EMA M5, TP {tp or 'EOD'}"] = r_for_tp(ub, tp)
    ub0 = store[(USER_BASE["range"], USER_BASE["sl"], "keiner")]
    variants["Nutzer-Basis ohne Trendfilter, TP EOD"] = r_for_tp(ub0, None)
    wt = store[(winner["range"], winner["sl"], winner["trend"])]
    wname = f"IS-Gewinner {'-'.join(winner['range'])}, SL {winner['sl']}, TP {winner['tp'] or 'EOD'}, Trend {winner['trend']}"
    variants[wname] = r_for_tp(wt, winner["tp"])

    old = pd.read_csv(ROOT / "ny_open_orb" / "results" / "is_only_7p_trades_tresor.csv")
    old = old[old.instrument == "NASDAQ"]
    for v, name in (("frueher", "Unser NASDAQ-ORB live (09:30-09:45, 0,6 ATR, EOD, ohne Mi)"),
                    ("IS-only", "Unser NASDAQ-ORB IS-only-Version (Tresor 10/25-09/26 durchgefallen)")):
        o = old[old.variant == v]
        variants[name] = pd.Series(o.r.to_numpy(), index=pd.to_datetime(o.time, utc=True).dt.tz_convert("America/New_York")).sort_index()

    comp, yearly = [], {}
    for name, r in variants.items():
        for part, rr in (("IS", lk.is_only(r)), ("OOS", lk.oos_only(r))):
            comp.append({"variante": name, "teil": part, **metrics(rr)})
        yearly[name] = pd.concat([lk.is_only(r), lk.oos_only(r)]).groupby(lambda x: x.year).sum()
    comp = pd.DataFrame(comp)
    comp.to_csv(OUT / "vergleich.csv", index=False)
    yr = pd.DataFrame(yearly).round(1)
    yr.to_csv(OUT / "jahre.csv")
    m_is = metrics(lk.is_only(variants[wname]))
    dsr = deflated_sharpe(m_is["avg"] / m_is["std"], m_is["n"], len(gi), m_is["skew"], m_is["kurt"], sr_var)
    print("\nVergleich:\n", comp[["variante", "teil", "n", "pro_jahr", "avg", "pf", "t", "sum", "dd", "win", "jahre_pos"]]
          .round(3).to_string(index=False))
    print("\nJahre (Σ R):\n", yr.to_string())
    print(f"\nDeflated Sharpe IS-Gewinner ({len(gi)} Versuche): {dsr:.3f}")

    # --- OOS-Bestenliste (nur Info, nicht Auswahl) ---------------------------
    go = grid[grid.teil == "OOS"].sort_values("t", ascending=False)
    go.head(15).to_csv(OUT / "oos_top15_info.csv", index=False)

    # --- Richtungsfilter ----------------------------------------------------
    states = filter_states(day_list)
    frows, trows = [], []
    bases = {"ohne EMA": store[(winner["range"], winner["sl"], "keiner")],
             "Nutzer-Basis ohne EMA": ub0}
    if lk.trials == len(RANGES) * len(SLS) * len(TPS) * len(TRENDS):   # Filter erst einmal zaehlen
        lk.log_trials(len(states) * 2 * len(bases), note="Richtungsfilter VIX/VIX-Trend/Realzins/Stress/Regime x allein/+EMA")
    for bname, t in bases.items():
        tp = winner["tp"] if bname == "ohne EMA" else None
        rng_end = winner["range"][1] if bname == "ohne EMA" else USER_BASE["range"][1]
        ema_tf = winner["trend"] if (bname == "ohne EMA" and winner["trend"] != "keiner") else "M5"
        ema = t["day"].map(ts_by_end[rng_end][ema_tf])
        r = r_for_tp(t, tp)
        t_is, r_is = lk.is_only(t), lk.is_only(r)
        t_oos, r_oos = lk.oos_only(t), lk.oos_only(r)
        ema_ok = (t["dir"] == ema)
        for fname, state in states.items():
            trows += state_table(t_is, r_is, state, "IS", fname) + state_table(t_oos, r_oos, state, "OOS", fname)
            rule = learn_rule(t_is, state, r_is)
            s = t["day"].map(state)
            keep = pd.Series([d in rule.get(z, ()) if isinstance(z, str) else False for z, d in zip(s, t["dir"])],
                             index=t.index)
            for vname, k in (("allein", keep), ("+EMA", keep & ema_ok)):
                for part, sl in (("IS", lk.is_only), ("OOS", lk.oos_only)):
                    kk, rr = sl(k), sl(r)
                    mk, mr = metrics(rr[kk]), metrics(rr[~kk])
                    frows.append({"basis": bname, "filter": fname, "variante": vname, "teil": part,
                                  "regel": json.dumps({z: list(v) for z, v in rule.items()}, ensure_ascii=False),
                                  "n_behalten": mk.get("n"), "avg_behalten": mk.get("avg"), "sum_behalten": mk.get("sum"),
                                  "t_behalten": mk.get("t"), "dd_behalten": mk.get("dd"),
                                  "n_entfernt": mr.get("n"), "avg_entfernt": mr.get("avg")})
        for part, sl in (("IS", lk.is_only), ("OOS", lk.oos_only)):
            for vname, k in (("Basis beide Seiten", pd.Series(True, index=t.index)), ("nur EMA", ema_ok)):
                kk, rr = sl(k), sl(r)
                mk = metrics(rr[kk])
                frows.append({"basis": bname, "filter": "-", "variante": vname, "teil": part, "regel": "",
                              "n_behalten": mk.get("n"), "avg_behalten": mk.get("avg"), "sum_behalten": mk.get("sum"),
                              "t_behalten": mk.get("t"), "dd_behalten": mk.get("dd")})
    fr = pd.DataFrame(frows)
    fr.to_csv(OUT / "filter.csv", index=False)
    pd.DataFrame(trows).to_csv(OUT / "filter_zustaende.csv", index=False)
    print("\nFilter:\n", fr.drop(columns="regel").round(3).to_string(index=False))
    print("\nZustaende:\n", pd.DataFrame(trows).round(3).to_string(index=False))

    (OUT / "summary.json").write_text(json.dumps({"winner": winner, "dsr": dsr, "versuche": lk.trials,
                                                  "n_is_zellen": int(len(gi)), "n_eligible": int(len(el))},
                                                 indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
