"""trend_pullback + gold_silver -- Realkosten-/Ausfuehrungs-Probe vor der Live-
Schaltung auf FK (p6_5-p6_8, Methode knowledge/areas/realkosten-und-ausfuehrungs-probe.md).

Nutzerauftrag 2026-10-04: "Ueberpruefe beide offenen Beine auf Ausfuehrungs-
logik, Versatz, Kostensensitivitaet und Optimierung hinsichtlich Ordersetzung,
und schaue, wie wir beide sicher live schalten koennen."

DIE ZENTRALE ABWEICHUNG (strategy/backtest.py::simulate_trades): Stop UND Ziel
werden nur auf den SCHLUSSKURS der Signal-Kerze (H1 bzw. H4) geprueft, der
Exit erfolgt zum Schlusskurs. Live (FKInstantFunding-MT5-Bridge::_process_leg)
liegt der SL beim Broker und greift INTRABAR; ein Broker-TP existiert fuer
diese Beine NICHT (BROKER_TP_R nur ctnl_reversal) -- das Ziel wird beim
naechsten stuendlichen Slow-Lauf zum Marktkurs geschlossen, nachdem der Scan
"target" meldet.

Nachgespielt auf M15-Kerzen der Order-Symbole (gold_silver handelt XAUUSD):
  engine         Backtest-Semantik (Referenz)
  live_heute     Einstieg Lag L, SL intrabar, Ziel per Scan (Kerzenschluss >= 2R
                 -> Exit zum Open der M15-Kerze ~20 Min. nach Kerzenschluss)
  broker_tp_X    Einstieg Lag L, SL intrabar, TP X*R intrabar beim Broker
Gates wie live: Restlaufzeit (SL vor Entry beruehrt -> kein Trade), 0,50R-
Detektor, Signalalter <= 60 Min. Gleiche M15-Kerze beruehrt SL und TP -> SL
(konservativ). Kosten = Round-Trip in bps je Markt, Staffel 0/1/2/3x.
IS 2019-2022 / OOS 2023-2026 fuer jede Parameterwahl.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import research_live_legs as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

START, END = "2018-06-01", L.END
H0 = pd.Timestamp("2019-01-01")
SPLIT = pd.Timestamp("2023-01-01")
BPS = {"GOLD": 0.79, "SILVER": 10.0, "PLATINUM": 10.0, "CHFJPY": 3.0, "USDJPY": 1.5}   # FK; nur GOLD gemessen
TF_H = {"GOLD": 1, "SILVER": 1, "PLATINUM": 1, "CHFJPY": 4, "USDJPY": 4}
SCAN_LAG_MIN = 20          # Slow-Lauf startet :14, Order ~:18-:20
OUT = REPO / "knowledge" / "_data" / "trend_gs_ausfuehrung.json"
REN = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}


def _naive_idx(df):
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df


def engine_trades():
    from combined_strategy.data import fetch_timeframe
    from mt5_gold_silver_divergenz.pipeline import run_pipeline as gs_pipeline
    from mt5_trend_pullback.filters import alignment_filter
    from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
    from strategy.backtest import BacktestConfig, simulate_trades

    cfg = BacktestConfig(spread_bps=0.0, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    gold_d1 = _naive_idx(fetch_timeframe("GOLD", "D1", START, END))["Close"]
    out = []
    for key in ("GOLD", "SILVER", "PLATINUM", "CHFJPY", "USDJPY"):
        df = fetch_timeframe(key, f"H{TF_H[key]}", START, END).rename(columns=REN)
        tr = simulate_trades(run_pipeline(df, adx_min=25.0), cfg)
        if key == "SILVER":
            tr = alignment_filter(tr, gold_d1)
        out.append(tr.assign(leg="trend_pullback", market=key, order_sym=key, tf_h=TF_H[key]))
    xau = fetch_timeframe("GOLD", "H4", START, END).rename(columns=REN)
    xag = fetch_timeframe("SILVER", "H4", START, END).rename(columns=REN)
    tr = simulate_trades(gs_pipeline(xau, xag, ret_len=25, band_lookback=50, band_mult=1.75, confirm_len=10), cfg)
    out.append(tr.assign(leg="gold_silver", market="GOLD", order_sym="GOLD", tf_h=4))
    t = pd.concat(out, ignore_index=True)
    for c in ("entry_time", "exit_time"):
        s = pd.to_datetime(t[c])
        t[c] = s.dt.tz_convert("UTC").dt.tz_localize(None) if s.dt.tz is not None else s
    t = t[t["entry_time"] >= H0].reset_index(drop=True)
    t["engine_r"] = t["direction"] * (t["exit_price"] - t["entry_price"]) / t["initial_risk"]
    return t


def m15_bars():
    from combined_strategy.data import fetch_timeframe
    return {k: _naive_idx(fetch_timeframe(k, "M15", START, END).rename(columns=REN))
            for k in ("GOLD", "SILVER", "PLATINUM", "CHFJPY", "USDJPY")}


def replay(t, bars, *, lag_min, mode, tp_r=2.0, cost_mult=1.0, gate_r=0.50, max_age=60):
    rows = []
    for x in t.itertuples():
        b = bars[x.order_sym]
        idx = b.index
        o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
        d = int(x.direction)
        e0, ir = float(x.entry_price), float(x.initial_risk)
        sl = e0 - d * ir
        i0 = idx.searchsorted(x.entry_time)
        ie = idx.searchsorted(x.entry_time + pd.Timedelta(minutes=lag_min))
        if ie >= len(idx) or i0 >= len(idx):
            continue
        rec = {"leg": x.leg, "market": x.market, "entry_time": x.entry_time, "engine_r": x.engine_r}
        if lag_min > max_age:
            rows.append({**rec, "status": "zu_alt"}); continue
        pre = slice(i0, ie)
        if ie > i0 and ((l[pre] <= sl).any() if d == 1 else (h[pre] >= sl).any()):
            rows.append({**rec, "status": "sl_vor_entry"}); continue
        P = o[ie]
        eff = d * (P - sl)
        if eff <= 0 or (ir - eff) / ir > gate_r:
            rows.append({**rec, "status": "r_gate"}); continue
        bps = BPS[x.order_sym] * cost_mult
        tp = P + d * tp_r * eff                       # Broker-TP ab Live-Fill (wie _broker_target)
        tp_scan = e0 + d * 2.0 * ir                   # Scan-Ziel: Engine-Bedingung ab Engine-Entry
        X, why, k = None, None, ie
        tf = pd.Timedelta(hours=int(x.tf_h))
        while k < len(idx):
            if (l[k] <= sl) if d == 1 else (h[k] >= sl):
                X, why = (min(o[k], sl) if d == 1 else max(o[k], sl)) if k > ie else sl, "stop"; break
            if mode == "broker" and ((h[k] >= tp) if d == 1 else (l[k] <= tp)):
                X, why = tp, "tp"; break
            if mode == "scan":
                bar_end = idx[k] + pd.Timedelta(minutes=15)
                if (bar_end - pd.Timestamp("2000-01-03")) % tf == pd.Timedelta(0) and d * (c[k] - tp_scan) >= 0:
                    j = idx.searchsorted(bar_end + pd.Timedelta(minutes=SCAN_LAG_MIN))
                    # zwischen Kerzenschluss und Scan kann noch der SL greifen
                    seg = slice(k + 1, min(j, len(idx)))
                    hit = np.flatnonzero((l[seg] <= sl) if d == 1 else (h[seg] >= sl))
                    if hit.size:
                        X, why = sl, "stop"
                    else:
                        X, why = (o[j] if j < len(idx) else c[-1]), "tp_scan"
                    break
            k += 1
        if X is None:
            rows.append({**rec, "status": "offen"}); continue
        r = (d * (X - P) - bps / 1e4 * P) / eff
        rows.append({**rec, "status": "gefuellt", "r": r, "why": why, "lev": ir / eff, "cost_r": bps / 1e4 * P / eff})
    return pd.DataFrame(rows)


def stats(df) -> dict:
    f = df[df["status"] == "gefuellt"] if "status" in df else df
    if f.empty:
        return {"n": 0}
    r = f["r"]
    w, lo = r[r > 0].sum(), -r[r < 0].sum()
    eq = r.cumsum()
    is_, oos = f[f["entry_time"] < SPLIT]["r"], f[f["entry_time"] >= SPLIT]["r"]
    return {"n": int(len(r)), "avg_r": round(float(r.mean()), 3), "pf": round(float(w / lo), 2) if lo else None,
            "sum_r": round(float(r.sum()), 1), "maxdd_r": round(float((eq - eq.cummax()).min()), 1),
            "is": round(float(is_.mean()), 3) if len(is_) else None, "oos": round(float(oos.mean()), 3) if len(oos) else None,
            "verworfen": {k: int(v) for k, v in df["status"].value_counts().items() if k != "gefuellt"} if "status" in df else {}}


def main() -> None:
    t = engine_trades()
    bars = m15_bars()
    res = {}
    for leg in ("trend_pullback", "gold_silver"):
        tl = t[t["leg"] == leg]
        print(f"\n################ {leg} -- {len(tl)} Engine-Trades ab 2019")
        eng = tl.assign(status="gefuellt", r=tl["engine_r"] - tl["order_sym"].map(BPS) / 1e4 * tl["entry_price"] / tl["initial_risk"])
        out = {"engine_mit_kosten": stats(eng)}
        print(f"  engine (Kerzenschluss, mit Kosten)  {out['engine_mit_kosten']}")

        print("  --- Versatz (live_heute: SL intrabar, Ziel per Scan) ---")
        for lag in (0, 15, 20, 30, 45, 60, 75):
            s = stats(replay(tl, bars, lag_min=lag, mode="scan"))
            out[f"live_heute_lag{lag}"] = s
            print(f"  lag {lag:3d} Min  {s}")
        print("  --- Broker-TP statt Scan-Ziel (Lag 20) ---")
        for tp in (1.5, 2.0, 2.5, 3.0, 4.0):
            s = stats(replay(tl, bars, lag_min=20, mode="broker", tp_r=tp))
            out[f"broker_tp{tp}_lag20"] = s
            print(f"  TP {tp:.1f}R        {s}")
        print("  --- Kosten-Staffel (Lag 20, Broker-TP 2R) ---")
        for cm in (0.0, 1.0, 2.0, 3.0):
            df = replay(tl, bars, lag_min=20, mode="broker", tp_r=2.0, cost_mult=cm)
            s = stats(df)
            out[f"kosten_x{cm}"] = s
            print(f"  Kosten x{cm:.0f}      {s}")
        df = replay(tl, bars, lag_min=20, mode="broker", tp_r=2.0)
        f = df[df["status"] == "gefuellt"]
        out["stop_gegen_kosten"] = {"stop_durch_rt_kosten_p5": round(float((1 / f["cost_r"]).quantile(.05)), 1),
                                    "median": round(float((1 / f["cost_r"]).median()), 1),
                                    "anteil_unter_3x": round(float((f["cost_r"] > 1 / 3).mean()), 3)}
        out["hebel"] = {"median": round(float(f["lev"].median()), 2), "max": round(float(f["lev"].max()), 2)}
        out["je_markt_broker_tp2"] = {m: stats(g) for m, g in df.groupby("market")}
        out["je_jahr_broker_tp2"] = f.groupby(f["entry_time"].dt.year)["r"].agg(["count", "mean"]).round(3).to_dict(orient="index")
        print(f"  Stop/Kosten: {out['stop_gegen_kosten']}  Hebel: {out['hebel']}")
        print("  je Markt (Broker-TP 2R):", {m: (v["n"], v.get("avg_r"), v.get("oos")) for m, v in out["je_markt_broker_tp2"].items()})
        print("  je Jahr:", {y: (v["count"], v["mean"]) for y, v in out["je_jahr_broker_tp2"].items()})
        res[leg] = out
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
