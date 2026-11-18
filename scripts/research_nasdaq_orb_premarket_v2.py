"""NASDAQ-ORB Vorboersen-Range, Runde 2 (Nutzerauftrag 15.11.2026).

Range 09:00-09:30 NY fest. Neu gegenueber Runde 1 (research_nasdaq_orb_premarket.py):
  - Stop-Order MIT PUFFER ueber/unter der Range (0 / 0,05 / 0,1 / 0,2 Range-Breiten), vor 09:30 beim Broker
    gelegt -> Einstieg als Stop-Order statt Market (Kosten: Spread + Stop-Slippage wie alle ORB-Laeufe).
  - Trendfilter-Kombinationen (EMA-Paare auf mehreren Zeitebenen, Paare von Zeitebenen, Gap, Vortag,
    Kurs vs. EMA200 D1), je in zwei umsetzbaren Formen:
      einseitig  = nur die Order in Trendrichtung liegt
      storno     = nur die Order in Trendrichtung, wird storniert, wenn der Kurs zuerst die Gegenseite der
                   Range (+Puffer) beruehrt (wie SP500-ORB live)
  - alles auf M1 gerechnet (Runde 1: M5 erzeugte Scheinverluste bei einseitigen Orders).
SL = anderes Range-Ende, TP 2/3/4/6 R oder Tagesschluss 15:59. Einstieg bis 11:59.

Lock wie Runde 1 (`nasdaq_orb_premarket_20261115`): IS 2016-07-28..2022-12-31 (Rangfolge), OOS bis
2026-05-14 (frei), Tresor zu. Versuche werden gezaehlt.

Kennzahlen: n, Trades/Jahr, Trefferquote, Ø R, PF, t, Sharpe je Trade, Sharpe annualisiert (Tages-R inkl.
Nulltage, x sqrt(252)), Σ R, MaxDD R, Σ/MaxDD, Jahre positiv, CAGR + MaxDD % bei 0,5 % Risiko (Zinseszins).

  python scripts/research_nasdaq_orb_premarket_v2.py
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
sys.path.insert(0, str(ROOT / "scripts"))

import research_nasdaq_orb_premarket as R1  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402

OUT = R1.OUT
RS, RE = 9 * 60, 9 * 60 + 30
CUT = 11 * 60 + 59
BUFFERS = [0.0, 0.05, 0.1, 0.2]
TPS = [2.0, 3.0, 4.0, 6.0, None]
RISK_PCT = 0.005
COST_BPS = R1.COST_BPS


# --------------------------------------------------------------------------- Daten
def load_m1() -> pd.DataFrame:
    df = fetch_m1("NASDAQ", R1.IS_START, R1.OOS_END)          # Tresor nie geladen
    return df[["open", "high", "low", "close"]].astype(float)


def day_arrays(m1: pd.DataFrame) -> dict:
    w = m1[(m1.index.time >= pd.Timestamp("09:00").time()) & (m1.index.time <= pd.Timestamp("15:59").time())]
    w = w[w.index.dayofweek < 5]
    out = {}
    for d, g in w.groupby(w.index.date):
        mins = (g.index.hour * 60 + g.index.minute).to_numpy()
        if len(g) < 350 or mins[-1] < 15 * 60 + 55 or ((mins >= RS) & (mins < RE)).sum() < 25:
            continue
        out[pd.Timestamp(d)] = dict(m=mins, o=g.open.to_numpy(), h=g.high.to_numpy(), l=g.low.to_numpy(),
                                    c=g.close.to_numpy())
    return out


# --------------------------------------------------------------------------- Trendfilter (+1/-1/0 je Tag)
def ema_sig(s: pd.Series, f: int, sl: int) -> pd.Series:
    return np.sign(s.ewm(span=f, adjust=False).mean() - s.ewm(span=sl, adjust=False).mean())


def tf_closes(m1: pd.DataFrame, rule: str) -> pd.Series:
    """Schlusskurse der Zeitebene, Stempel = Zeitpunkt, ab dem die Kerze bekannt ist."""
    c = m1["close"].resample(rule, label="left", closed="left").last().dropna()
    c.index = c.index + pd.Timedelta(rule)
    return c


def build_trends(m1: pd.DataFrame, days: list) -> dict[str, dict]:
    t930 = {d: pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30) for d in days}
    sess = m1[(m1.index.time >= pd.Timestamp("09:30").time()) & (m1.index.time <= pd.Timestamp("15:59").time())]
    g = sess.groupby(sess.index.date)
    d_close = g["close"].last(); d_close.index = pd.to_datetime(d_close.index)
    d_open = g["open"].first(); d_open.index = pd.to_datetime(d_open.index)

    def asof_intraday(sig: pd.Series) -> dict:
        return {d: float(sig.asof(t)) if t >= sig.index[0] else 0.0 for d, t in t930.items()}

    def prior_daily(sig: pd.Series) -> dict:
        out = {}
        for d in days:
            p = sig[sig.index < d]
            out[d] = float(p.iloc[-1]) if len(p) else 0.0
        return out

    tf = {k: tf_closes(m1, r) for k, r in (("M5", "5min"), ("M15", "15min"), ("H1", "1h"), ("H4", "4h"))}
    raw = {}
    for name, (k, f, s) in {"EMA50/200 M5": ("M5", 50, 200), "EMA50/200 M15": ("M15", 50, 200),
                            "EMA50/200 H1": ("H1", 50, 200), "EMA50/200 H4": ("H4", 50, 200),
                            "EMA20/50 M15": ("M15", 20, 50), "EMA20/50 H1": ("H1", 20, 50),
                            "EMA9/21 M5": ("M5", 9, 21), "EMA9/21 H1": ("H1", 9, 21)}.items():
        raw[name] = asof_intraday(ema_sig(tf[k], f, s))
    raw["EMA50/200 D1"] = prior_daily(ema_sig(d_close, 50, 200))
    raw["EMA20/50 D1"] = prior_daily(ema_sig(d_close, 20, 50))
    # Kurs um 09:29 gegen EMA200 der Vortagesschluesse
    ema200 = d_close.ewm(span=200, adjust=False).mean()
    c929 = m1["close"]
    px = {d: float(c929.asof(t - pd.Timedelta(minutes=1))) for d, t in t930.items()}
    raw["Kurs vs EMA200 D1"] = {d: float(np.sign(px[d] - ema200[ema200.index < d].iloc[-1])) if (ema200.index < d).any()
                                else 0.0 for d in days}
    prev_close = {d: (d_close[d_close.index < d].iloc[-1] if (d_close.index < d).any() else np.nan) for d in days}
    raw["Gap (09:29 vs Vortagesschluss)"] = {d: float(np.sign(px[d] - prev_close[d])) if not pd.isna(prev_close[d])
                                             else 0.0 for d in days}
    vt = np.sign(d_close - d_open)
    raw["Vortag-Kerze"] = prior_daily(vt)

    def both(a, b):
        return {d: (raw[a][d] if raw[a][d] == raw[b][d] else 0.0) for d in days}

    combos = {"D1 + H1 (EMA50/200)": ("EMA50/200 D1", "EMA50/200 H1"),
              "D1 + M15 (EMA50/200)": ("EMA50/200 D1", "EMA50/200 M15"),
              "H4 + H1 (EMA50/200)": ("EMA50/200 H4", "EMA50/200 H1"),
              "D1 EMA + Gap": ("EMA50/200 D1", "Gap (09:29 vs Vortagesschluss)"),
              "H1 EMA + Gap": ("EMA50/200 H1", "Gap (09:29 vs Vortagesschluss)"),
              "Kurs>EMA200 D1 + H1 EMA20/50": ("Kurs vs EMA200 D1", "EMA20/50 H1")}
    for n, (a, b) in combos.items():
        raw[n] = both(a, b)
    return raw


# --------------------------------------------------------------------------- Simulation
def sim_day(a: dict, buf: float, allowed: tuple, storno: bool) -> dict | None:
    m, o, h, l, c = a["m"], a["o"], a["h"], a["l"], a["c"]
    rm = (m >= RS) & (m < RE)
    rh, rl = h[rm].max(), l[rm].min()
    w = rh - rl
    if w <= 0 or not allowed:
        return None
    up_lv, dn_lv = rh + buf * w, rl - buf * w
    e, d = None, 0
    for j in np.where((m >= RE) & (m <= CUT))[0]:
        up_touch, dn_touch = h[j] >= up_lv, l[j] <= dn_lv
        if storno and len(allowed) == 1:
            other = dn_touch if allowed[0] == 1 else up_touch
            mine = up_touch if allowed[0] == 1 else dn_touch
            if other and mine:   # beide in derselben Minute: naeher am Open zuerst
                first_mine = (abs(up_lv - o[j]) <= abs(o[j] - dn_lv)) == (allowed[0] == 1)
                if not first_mine:
                    return None
            elif other:
                return None
        up = 1 in allowed and up_touch
        dn = -1 in allowed and dn_touch
        if up and dn:
            d = 1 if abs(up_lv - o[j]) <= abs(o[j] - dn_lv) else -1
        elif up:
            d = 1
        elif dn:
            d = -1
        if d:
            e = j
            break
    if e is None:
        return None
    p = max(o[e], up_lv) if d == 1 else min(o[e], dn_lv)
    sl = rl if d == 1 else rh
    risk = abs(p - sl)
    cost_r = p * COST_BPS / 1e4 / risk
    if (d == 1 and l[e] <= sl) or (d == -1 and h[e] >= sl):
        return dict(dir=d, risk=risk, mfe=0.0, sl_hit=True, sl_r=-1.0, eod_r=np.nan, cost_r=cost_r, entry_min=int(m[e]))
    k_sl, sl_r = None, -1.0
    for j in range(e + 1, len(m)):
        if (d == 1 and l[j] <= sl) or (d == -1 and h[j] >= sl):
            k_sl = j
            fill = min(o[j], sl) if d == 1 else max(o[j], sl)
            sl_r = (fill - p) * d / risk
            break
    stop = k_sl if k_sl is not None else len(m)
    mfe = (((h[e + 1:stop].max() - p) if d == 1 else (p - l[e + 1:stop].min())) / risk) if stop > e + 1 else 0.0
    return dict(dir=d, risk=risk, mfe=mfe, sl_hit=k_sl is not None, sl_r=sl_r, eod_r=(c[-1] - p) * d / risk,
                cost_r=cost_r, entry_min=int(m[e]))


def run(days: dict, buf: float, trend: dict | None, storno: bool) -> pd.DataFrame:
    rows = []
    for d, a in days.items():
        if trend is None:
            al = (1, -1)
        else:
            v = trend.get(d, 0.0)
            al = (1,) if v > 0 else (-1,) if v < 0 else ()
        x = sim_day(a, buf, al, storno)
        if x:
            x["day"] = d
            rows.append(x)
    t = pd.DataFrame(rows)
    t.index = pd.DatetimeIndex([pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(minutes=int(mm))
                                for d, mm in zip(t.day, t.entry_min)])
    return t.sort_index()


# --------------------------------------------------------------------------- Kennzahlen
def stats(r: pd.Series, all_days: pd.DatetimeIndex) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {"n": len(r)}
    yrs = (all_days.max() - all_days.min()).days / 365.25
    std = r.std(ddof=1)
    loss = -r[r < 0].sum()
    daily = r.groupby(r.index.tz_localize(None).normalize()).sum().reindex(all_days, fill_value=0.0)
    eq = daily.cumsum()
    dd_r = float((eq - eq.cummax()).min())
    acc = (1 + RISK_PCT * daily).cumprod()
    half = len(r) // 2
    yr = r.groupby(r.index.year).sum()
    return {"n": len(r), "trades_jahr": len(r) / yrs, "win": (r > 0).mean(), "avg_r": r.mean(),
            "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "t": r.mean() / std * np.sqrt(len(r)),
            "sharpe_trade": r.mean() / std, "sharpe_ann": daily.mean() / daily.std() * np.sqrt(252),
            "sum_r": r.sum(), "maxdd_r": dd_r, "sum_dd": r.sum() / -dd_r if dd_r < 0 else np.inf,
            "jahre_pos": f"{int((yr > 0).sum())}/{len(yr)}",
            "cagr_05": acc.iloc[-1] ** (1 / yrs) - 1, "maxdd_pct_05": float((acc / acc.cummax() - 1).min()),
            "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum()}


def r_for_tp(t, tp, cost_mult=1.0):
    t = t.assign(cost_r=t.cost_r * cost_mult)
    return R1.r_for_tp(t, tp)


# --------------------------------------------------------------------------- Hauptlauf
def main() -> int:
    lk = R1.lock()
    m1 = load_m1()
    days = day_arrays(m1)
    dl = sorted(days)
    print(f"{len(dl)} Tage", flush=True)
    trends = build_trends(m1, dl)
    filt = [("keiner", None, False)] + [(n, trends[n], s) for n in trends for s in (False, True)]
    n_var = len(filt) * len(BUFFERS) * len(TPS)
    if lk.trials <= 700:   # Runde 1 = 658 Versuche; Runde 2 nur einmal zaehlen
        lk.log_trials(n_var, note="Runde 2: Puffer x Trendfilter(einseitig/storno) x TP, M1")

    idx = pd.DatetimeIndex(dl)
    is_days = idx[(idx >= R1.IS_START) & (idx <= R1.IS_END)]
    oos_days = idx[(idx > R1.IS_END) & (idx <= R1.OOS_END)]
    rows, keep = [], {}
    for (fname, tr, storno), buf in itertools.product(filt, BUFFERS):
        t = run(days, buf, tr, storno)
        mode = "-" if tr is None else ("Storno" if storno else "einseitig")
        for tp in TPS:
            r = r_for_tp(t, tp)
            key = (fname, mode, buf, tp)
            keep[key] = r
            for part, rr, dd in (("IS", lk.is_only(r), is_days), ("OOS", lk.oos_only(r), oos_days)):
                rows.append({"filter": fname, "modus": mode, "puffer": buf, "tp": tp if tp else "EOD", "teil": part,
                             **stats(rr, dd)})
        print(f"  {fname} {mode} Puffer {buf}: {len(t)} Trades", flush=True)
    g = pd.DataFrame(rows)
    g.to_csv(OUT / "v2_grid.csv", index=False)

    k = ["filter", "modus", "puffer", "tp"]
    w = g[g.teil == "IS"].set_index(k).add_prefix("IS_").join(g[g.teil == "OOS"].set_index(k).add_prefix("OOS_"))
    w = w.reset_index()
    w["ok"] = (w.IS_n >= 100) & (w.IS_h1 > 0) & (w.IS_h2 > 0)
    w = w.sort_values(["ok", "IS_sharpe_ann"], ascending=[False, False])
    w["rang_IS"] = range(1, len(w) + 1)
    w.to_csv(OUT / "v2_rangliste.csv", index=False)

    # Kostenstress fuer die IS-Top-15
    top = w.head(15)
    cs = []
    for _, row in top.iterrows():
        tp = None if row.tp == "EOD" else float(row.tp)
        fname, mode, buf = row["filter"], row.modus, row.puffer
        tr = None if fname == "keiner" else trends[fname]
        t = run(days, buf, tr, mode == "Storno")
        for mult in (2.0, 3.0):
            r = r_for_tp(t, tp, mult)
            cs.append({"rang_IS": row.rang_IS, "kosten": f"x{mult:g}",
                       "IS_avg_r": lk.is_only(r).mean(), "IS_sharpe_ann": stats(lk.is_only(r), is_days)["sharpe_ann"],
                       "OOS_avg_r": lk.oos_only(r).mean(), "OOS_sharpe_ann": stats(lk.oos_only(r), oos_days)["sharpe_ann"]})
    pd.DataFrame(cs).to_csv(OUT / "v2_kostenstress_top15.csv", index=False)

    # Puffer-Uebersicht ohne Filter
    pd.set_option("display.width", 300)
    cols = ["rang_IS", "filter", "modus", "puffer", "tp", "IS_n", "IS_avg_r", "IS_pf", "IS_sharpe_ann", "IS_maxdd_r",
            "OOS_n", "OOS_avg_r", "OOS_pf", "OOS_sharpe_ann", "OOS_maxdd_r", "OOS_jahre_pos"]
    print(w[cols].head(40).round(3).to_string(index=False))
    print(pd.DataFrame(cs).round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
