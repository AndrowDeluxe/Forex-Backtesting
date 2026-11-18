"""Tresor-Pruefung NASDAQ-ORB Vorboersen-Range (eingefroren 15.11.2026, Hash 53908ff0...).

Oeffnet den Tresor (15.05.-14.11.2026) des Locks `nasdaq_orb_premarket_20261115` genau einmal und rechnet die
eingefrorenen Kandidaten A-F und den Live-NASDAQ-ORB:

1. TICK-SIMULATION auf echten Broker-Ticks (data_cache/broker_ticks, scripts/pull_broker_ticks_nasdaq.py):
   Range aus Bid (MT5-Chart), Buy-Stop loest bei Ask >= Level aus, Sell-Stop bei Bid <= Level, Fuellung am
   ausloesenden Tick. SL ebenso (Long-SL: Bid <= SL, Short-SL: Ask >= SL). Ausstieg letzter Tick vor 16:00
   (Long Bid, Short Ask). R auf das GEPLANTE Risiko (so sized die Bridge). Kommission 0 (echte Deals: 0).
   Serverzeit -> NY je Tag ueber die beste Korrelation der M1-Renditen mit Dukascopy (Versatz 5..8 h).
2. DUKASCOPY-M1 mit Standardkosten (1,29 bps) und mit den auf Ticks gemessenen Kosten je Trade.

Trendzustaende kommen aus Dukascopy (nur abgeschlossene Kerzen vor 09:30), damit alle Broker dieselben
Filtersignale bekommen.

  python scripts/research_nasdaq_orb_premarket_tresor.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import research_nasdaq_orb_premarket as R1  # noqa: E402
import research_nasdaq_orb_premarket_v2 as R2  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402

OUT = R1.OUT
TICKS = ROOT / "data_cache" / "broker_ticks"
TRESOR_START, TRESOR_END = "2026-05-15", "2026-11-14"
BROKERS = {"TTP": "TTP_USTEC.parquet", "Tickmill": "Tickmill_USTEC.parquet", "IQ": "IQ_NAS100.gbe.parquet"}
FREEZE = json.loads((OUT / "tresor_freeze.json").read_text(encoding="utf-8"))
CANDS = FREEZE["kandidaten"]
LIVE_STOP_ATR = 0.6


# --------------------------------------------------------------------------- Kennzahlen
def stats(r: pd.Series, days: pd.DatetimeIndex) -> dict:
    r = r.dropna()
    ix = pd.DatetimeIndex(r.index)
    if ix.tz is not None:
        r = pd.Series(r.to_numpy(), index=ix.tz_convert("America/New_York").tz_localize(None))
    if len(r) < 3:
        return {"n": len(r), "sum_r": r.sum() if len(r) else 0.0}
    std = r.std(ddof=1)
    loss = -r[r < 0].sum()
    daily = r.groupby(pd.DatetimeIndex(r.index).normalize()).sum().reindex(days, fill_value=0.0)
    eq = daily.cumsum()
    acc = (1 + 0.005 * daily).cumprod()
    return {"n": len(r), "win": (r > 0).mean(), "avg_r": r.mean(), "pf": r[r > 0].sum() / loss if loss > 0 else np.inf,
            "t": r.mean() / std * np.sqrt(len(r)), "sum_r": r.sum(), "maxdd_r": float((eq - eq.cummax()).min()),
            "sharpe_ann": daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else np.nan,
            "rendite_05": acc.iloc[-1] - 1, "maxdd_pct_05": float((acc / acc.cummax() - 1).min())}


# --------------------------------------------------------------------------- Ticks
def load_ticks(fname: str) -> pd.DataFrame:
    df = pd.read_parquet(TICKS / fname)
    df["ts"] = pd.to_datetime(df.time_msc, unit="ms")          # naive Serverzeit
    return df.drop(columns="time_msc").sort_values("ts").reset_index(drop=True)


def ny_ticks_by_day(ticks: pd.DataFrame, duk_m1: pd.DataFrame) -> tuple[dict, dict]:
    """Je Handelstag: Ticks mit NY-Zeit (Sekunden seit Mitternacht). Versatz je Tag ueber M1-Korrelation."""
    duk = duk_m1["close"].copy()
    duk.index = duk.index.tz_localize(None)
    out, offs = {}, {}
    srv_day = (ticks.ts - pd.Timedelta(hours=14)).dt.normalize()     # Fenster 14:50..00:05 gehoert zum Starttag
    for d, g in ticks.groupby(srv_day):
        mb = g.set_index("ts")["bid"].resample("1min").last().dropna()
        best, best_c = None, -2.0
        for h in (5, 6, 7, 8):
            ny = mb.copy()
            ny.index = ny.index - pd.Timedelta(hours=h)
            ny = ny[(ny.index >= d + pd.Timedelta(hours=9, minutes=30)) & (ny.index < d + pd.Timedelta(hours=16))]
            dd = duk.reindex(ny.index)
            j = pd.concat([ny.diff(), dd.diff()], axis=1).dropna()
            if len(j) < 100:
                continue
            c = j.corr().iloc[0, 1]
            if c > best_c:
                best, best_c = h, c
        if best is None or best_c < 0.8:
            continue
        nt = g.ts - pd.Timedelta(hours=best)
        sec = ((nt - d).dt.total_seconds()).to_numpy()
        keep = (sec >= 9 * 3600) & (sec < 16 * 3600)
        out[d] = dict(s=sec[keep], bid=g.bid.to_numpy()[keep], ask=g.ask.to_numpy()[keep])
        offs[d] = (best, round(best_c, 3))
    return out, offs


def _first(mask: np.ndarray) -> int:
    i = int(np.argmax(mask))
    return i if mask.size and mask[i] else -1


def tick_trade_new(a: dict, buf: float, allowed: tuple, storno: bool) -> dict | None:
    s, bid, ask = a["s"], a["bid"], a["ask"]
    rm = (s >= 9 * 3600) & (s < 9.5 * 3600)
    if rm.sum() < 50 or not allowed:
        return None
    rh, rl = bid[rm].max(), bid[rm].min()
    w = rh - rl
    up, dn = rh + buf * w, rl - buf * w
    win = np.where((s >= 9.5 * 3600) & (s < 12 * 3600))[0]
    if win.size == 0:
        return None
    iu = _first(ask[win] >= up) if 1 in allowed or (storno and -1 in allowed) else -1
    idn = _first(bid[win] <= dn) if -1 in allowed or (storno and 1 in allowed) else -1
    cand = []
    if 1 in allowed and iu >= 0:
        cand.append((iu, 1))
    if -1 in allowed and idn >= 0:
        cand.append((idn, -1))
    if not cand:
        return None
    k, d = min(cand)
    if storno and len(allowed) == 1:
        other = idn if d == 1 else iu
        if other >= 0 and other < k:
            return None
    e = win[k]
    level = up if d == 1 else dn
    fill = ask[e] if d == 1 else bid[e]
    sl = rl if d == 1 else rh
    risk = abs(level - sl)
    after = np.arange(e + 1, s.size)
    hit = _first(bid[after] <= sl) if d == 1 else _first(ask[after] >= sl)
    if hit >= 0:
        j = after[hit]
        exit_p = bid[j] if d == 1 else ask[j]
        ideal_exit = sl
    else:
        exit_p = bid[-1] if d == 1 else ask[-1]
        ideal_exit = (bid[-1] + ask[-1]) / 2
    r = (exit_p - fill) * d / risk
    r_ideal = (ideal_exit - level) * d / risk
    return dict(dir=d, r=r, r_ideal=r_ideal, entry_slip=(fill - level) * d, exit_cost=(ideal_exit - exit_p) * d,
                price=level, risk=risk, entry_sec=float(s[e]), sl_hit=hit >= 0,
                spread_open=float(np.median((ask - bid)[(s >= 9.5 * 3600) & (s < 9.5 * 3600 + 60)])))


def tick_trade_live(a: dict, atr: float) -> dict | None:
    s, bid, ask = a["s"], a["bid"], a["ask"]
    rm = (s >= 9.5 * 3600) & (s < 9.75 * 3600)
    if rm.sum() < 50 or not atr or np.isnan(atr):
        return None
    hi, lo = bid[rm].max(), bid[rm].min()
    sl = {1: hi - LIVE_STOP_ATR * atr, -1: lo + LIVE_STOP_ATR * atr}
    win = np.where(s >= 9.75 * 3600)[0]
    ev = []
    for d, trig, canc in ((1, ask[win] >= hi, bid[win] <= sl[1]), (-1, bid[win] <= lo, ask[win] >= sl[-1])):
        it, ic = _first(trig), _first(canc)
        if it >= 0 and (ic < 0 or it <= ic):   # gleicher Tick: Fill zuerst
            ev.append((it, d))
    if not ev:
        return None
    k, d = min(ev)
    e = win[k]
    level = hi if d == 1 else lo
    fill = ask[e] if d == 1 else bid[e]
    risk = LIVE_STOP_ATR * atr
    after = np.arange(e + 1, s.size)
    hit = _first(bid[after] <= sl[d]) if d == 1 else _first(ask[after] >= sl[d])
    if hit >= 0:
        j = after[hit]
        exit_p, ideal_exit = (bid[j] if d == 1 else ask[j]), sl[d]
    else:
        exit_p, ideal_exit = (bid[-1] if d == 1 else ask[-1]), (bid[-1] + ask[-1]) / 2
    return dict(dir=d, r=(exit_p - fill) * d / risk, r_ideal=(ideal_exit - level) * d / risk,
                entry_slip=(fill - level) * d, exit_cost=(ideal_exit - exit_p) * d, price=level, risk=risk,
                entry_sec=float(s[e]), sl_hit=hit >= 0,
                spread_open=float(np.median((ask - bid)[(s >= 9.75 * 3600) & (s < 9.75 * 3600 + 60)])))


# --------------------------------------------------------------------------- Hauptlauf
def main() -> int:
    lk = R1.lock()
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if "tresor" not in st["unsealed"]:
        print("Tresor geoeffnet:", lk.unseal("tresor", FREEZE["hash"]), flush=True)
    else:
        print("Tresor war bereits geoeffnet am", st["unsealed"]["tresor"], "- nur Auswertung", flush=True)

    m1_raw = fetch_m1("NASDAQ", R1.IS_START, TRESOR_END)
    m1 = m1_raw[["open", "high", "low", "close"]].astype(float)
    days_all = R2.day_arrays(m1)
    dl = sorted(days_all)
    trends = R2.build_trends(m1, dl)
    t_days = pd.DatetimeIndex([d for d in dl if d >= pd.Timestamp(TRESOR_START)])
    days_t = {d: days_all[d] for d in t_days}
    print(f"Tresor-Tage Dukascopy: {len(t_days)}", flush=True)

    def allowed(fname, d):
        if fname == "keiner":
            return (1, -1)
        v = trends[fname].get(d, 0.0)
        return (1,) if v > 0 else (-1,) if v < 0 else ()

    # Live-ORB (Dukascopy) fuer ATR und Dukascopy-Vergleich
    from research_orb_is_only_reopt import LIVE, run_config, allowed_for  # noqa: F401
    from ny_open_orb import regime
    m15 = fetch_m15("NASDAQ", R1.IS_START, TRESOR_END)
    frame = build_frame(m15, m1_raw.loc["2026-01-01":], range_bars=1)
    sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
    bias = regime.ema_trend_bias(m15, sessions)
    r_live, cost_live = run_config({1: frame}, sessions, bias, "NASDAQ", LIVE["NASDAQ"])
    r_live = r_live[r_live.index >= pd.Timestamp(TRESOR_START, tz=r_live.index.tz)]
    atr_by_day = frame.groupby("session")["atr"].first()
    ai = pd.DatetimeIndex(pd.to_datetime(atr_by_day.index))
    if ai.tz is not None:
        ai = ai.tz_convert("America/New_York").tz_localize(None)
    atr_by_day.index = ai.normalize()

    rows, trades_out = [], []

    # ---- Ticks je Broker -----------------------------------------------------
    cost_new, cost_live_ticks = [], []
    for broker, fname in BROKERS.items():
        if not (TICKS / fname).exists():
            continue
        tk = load_ticks(fname)
        byday, offs = ny_ticks_by_day(tk, m1.loc[TRESOR_START:])
        del tk
        bdays = pd.DatetimeIndex(sorted(d for d in byday if d in days_t))
        print(f"{broker}: {len(bdays)} Tage mit Ticks, Versatz {pd.Series([o[0] for o in offs.values()]).value_counts().to_dict()}",
              flush=True)
        for cname, c in CANDS.items():
            res = []
            for d in bdays:
                x = tick_trade_new(byday[d], c["puffer"], allowed(c["filter"], d), c["modus"] == "Storno")
                if x:
                    x["day"] = d
                    res.append(x)
            t = pd.DataFrame(res).set_index("day")
            if cname.startswith("B"):
                cost_new.append(t)
            for kind in ("r", "r_ideal"):
                rows.append({"quelle": f"Ticks {broker}", "kosten": "echt" if kind == "r" else "ohne (Level/Mitte)",
                             "variante": cname, **stats(t[kind], bdays)})
            trades_out.append(t.assign(quelle=broker, variante=cname))
        res = []
        for d in bdays:
            if d.day_name() == "Wednesday":
                continue
            x = tick_trade_live(byday[d], float(atr_by_day.get(d, np.nan)))
            if x:
                x["day"] = d
                res.append(x)
        t = pd.DataFrame(res).set_index("day")
        cost_live_ticks.append(t)
        for kind in ("r", "r_ideal"):
            rows.append({"quelle": f"Ticks {broker}", "kosten": "echt" if kind == "r" else "ohne (Level/Mitte)",
                         "variante": "LIVE_ORB", **stats(t[kind], bdays)})
        trades_out.append(t.assign(quelle=broker, variante="LIVE_ORB"))

    # ---- gemessene Kosten -> bps --------------------------------------------
    cn = pd.concat(cost_new)
    cl = pd.concat(cost_live_ticks)
    meas = {"neu_bps": float(((cn.entry_slip + cn.exit_cost) / cn.price * 1e4).mean()),
            "live_bps": float(((cl.entry_slip + cl.exit_cost) / cl.price * 1e4).mean()),
            "neu_entry_pts_median": float(cn.entry_slip.median()), "neu_exit_pts_median": float(cn.exit_cost.median()),
            "live_entry_pts_median": float(cl.entry_slip.median()), "live_exit_pts_median": float(cl.exit_cost.median()),
            "spread_0930_pts_median": float(cn.spread_open.median()), "spread_0945_pts_median": float(cl.spread_open.median())}
    print("Gemessene Kosten:", json.dumps({k: round(v, 3) for k, v in meas.items()}), flush=True)

    # ---- Dukascopy -----------------------------------------------------------
    for cname, c in CANDS.items():
        tr = None if c["filter"] == "keiner" else trends[c["filter"]]
        t = R2.run(days_t, c["puffer"], tr, c["modus"] == "Storno")
        t_std = R1.r_for_tp(t, None)
        t_meas = R1.r_for_tp(t.assign(cost_r=t.cost_r / R1.COST_BPS * meas["neu_bps"]), None)
        rows.append({"quelle": "Dukascopy", "kosten": "Standard 1,29 bps", "variante": cname, **stats(t_std, t_days)})
        rows.append({"quelle": "Dukascopy", "kosten": f"gemessen {meas['neu_bps']:.2f} bps", "variante": cname,
                     **stats(t_meas, t_days)})
    rows.append({"quelle": "Dukascopy", "kosten": "Standard 1,29 bps", "variante": "LIVE_ORB",
                 **stats(r_live.tz_localize(None) if r_live.index.tz else r_live, t_days)})
    r_live_meas = (r_live + cost_live.reindex(r_live.index) - cost_live.reindex(r_live.index) / R1.COST_BPS * meas["live_bps"])
    r_live_meas.index = r_live_meas.index.tz_localize(None)
    rows.append({"quelle": "Dukascopy", "kosten": f"gemessen {meas['live_bps']:.2f} bps", "variante": "LIVE_ORB",
                 **stats(r_live_meas, t_days)})

    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "tresor_report.csv", index=False)
    pd.concat(trades_out).to_csv(OUT / "tresor_trades_ticks.csv")
    (OUT / "tresor_kosten_gemessen.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
