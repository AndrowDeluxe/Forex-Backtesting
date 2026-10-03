"""CTNL-Reversal: beste SL/TP/Zeit-Exit-Variante unter Kosten, Versatz und
Live-Timing (2026-10-03, Nutzerauftrag "teste unter Kosten, Versatz und
Timing die beste SL und TP Variante oder einen zeitbasierten Ausstieg und
lege ihn fuer alle Bridges fest").

Grundlage wie research_ctnl_entry_versatz.py: ribbon-konforme Signale mit
Spike >= 0,75 ATR. Einstieg 15 Min. nach dem Backtest-Fill (Live-Takt seit
03.10., alle drei Bridges). Live-Gates: Restlaufzeit (Signal-SL vor Entry
beruehrt -> kein Trade) und R-Detektor 0,50R. Positionsdeckel 2 je Variante
mit deren EIGENEN Exits (so zaehlt die Bridge echte Broker-Positionen).

Grid:
  k        SL-Abstand am Signal-Trigger (Hoch/Tief der Signalbar) in ATR
  stop     "touch" = Broker-SL bei k (Beruehrung, M5)
           "close" = Stop auf M15-Schlusskurs bei k, Ausfuehrung 5 Min. spaeter
                     (Poll), dazu Notfall-Broker-SL bei 2k. Sizing auf k.
  tp       R-Vielfaches als Broker-TP (Beruehrung), None = keins
  hold     Zeit-Exit in Tagen (10 = praktisch keiner)
Referenzen: "live_funded" (k=3 touch, TP 5R auf M15-Schluss gepollt, 4 Tage
gepollt -- heutiger Funded/FK-Stand) und "live_ek" (SL-Distanz am Live-Kurs,
TP 5R Broker, kein Zeit-Exit).

Kosten: Round-Trip-Spread in bps (TTP 2,01 / IQ 0,73) je zur Haelfte, dazu
Swap SWAP_BPS_PRO_TAG je angefangenem Haltetag (Annahme, keine Messung im
Repo). R = Ergebnis / Sizing-Distanz.

Aufruf: python scripts/research_ctnl_exit_optimierung.py --cache <pkl>
"""

from __future__ import annotations

import argparse
import itertools
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_DIR), str(REPO_DIR / "scripts"), str(REPO_DIR / "ou_paper_backtest")]

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.spike_gate import SPIKE_MIN_ATR  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive  # noqa: E402
from strategy.backtest import BacktestConfig  # noqa: E402

VERSATZ = pd.Timedelta(minutes=15)
POLL = 1                 # M5-Bars zwischen M15-Schluss und Ausfuehrung
MAX_TAGE = 10
N_M5 = 12 * 24 * MAX_TAGE
MAX_CONSUMED_R = 0.50
RISK = 0.0015
KOSTEN = {"ttp": 2.01, "iq": 0.73}
SWAP_BPS_PRO_TAG = 1.5
ALLE_SIGNALE = False

K_GRID = [1.5, 2.0, 2.5, 3.0, 4.0]
STOP_GRID = ["touch", "close"]
TP_GRID = [2.0, 3.0, 4.0, 5.0, 7.0, None]
HOLD_GRID = [1, 2, 4, 10]


def lade(cache: Path):
    d = pickle.load(open(cache, "rb"))
    return d["bars"], d["rib"], d["sig"]


def kandidaten(rib, sig) -> pd.DataFrame:
    """Live-getreue Auswahl: wie _scan_ctnl() erst die Simulations-Kappung auf
    REV_MAX_CONCURRENT (mit den Sim-Exits, VOR den Filtern), dann Ribbon und
    Spike. Der Broker-Deckel kommt danach je Variante mit deren eigenen Exits.
    --alle-signale: Filter vor Kappung (nicht live, nur als Vergleich)."""
    cfg = BacktestConfig(spread_bps=8.0, stop_atr_mult=3.0, use_vwap_target=False,
                         take_profit_r=5.0, max_hold_bars=96 * 4)
    tr = simulate_trades_concurrent(sig, cfg)
    if not ALLE_SIGNALE:
        tr = _cap_concurrent(tr, REV_MAX_CONCURRENT)
    row = sig.iloc[tr["signal_bar"].to_numpy()]
    tr = tr.assign(spike=((row["high"] - row["low"]) / row["atr"]).to_numpy())
    tr["et"] = _utc_naive(tr["entry_time"])
    tr["rib"] = rib.reindex(tr["et"], method="ffill").to_numpy()
    ok = ((tr["direction"] == 1) & (tr["rib"] > 0)) | ((tr["direction"] == -1) & (tr["rib"] < 0))
    tr = tr[ok & (tr["spike"] >= SPIKE_MIN_ATR)].copy()
    d = tr["direction"].to_numpy()
    stop3 = tr["entry_price"].to_numpy() - d * tr["initial_risk"].to_numpy()
    tr["atr"] = tr["atr_at_entry"]
    tr["trigger"] = stop3 + d * 3.0 * tr["atr"].to_numpy()
    tr["sim_dist"] = tr["initial_risk"]
    return tr.sort_values("et").reset_index(drop=True)


class Pfade:
    """M5-Pfad je Signal ab Backtest-Fill, einmal vorberechnet."""

    def __init__(self, tr: pd.DataFrame, m5: pd.DataFrame):
        idx = _utc_naive(m5.index)
        o, h, l, c = (m5[x].to_numpy() for x in ("open", "high", "low", "close"))
        mins = idx.minute.to_numpy()
        self.items = []
        for _, t in tr.iterrows():
            k0 = idx.searchsorted(t["et"])
            ke = idx.searchsorted(t["et"] + VERSATZ)
            if ke + 10 >= len(o) or idx[ke] - t["et"] > pd.Timedelta(hours=2):
                continue  # Datenluecke (Wochenende/Pause) -- nicht modellierbar
            end = min(len(o), ke + N_M5)
            self.items.append({
                "t": t, "pre_h": h[k0:ke], "pre_l": l[k0:ke], "pre_c": c[ke - 1],
                "o": o[ke:end], "h": h[ke:end], "l": l[ke:end], "c": c[ke:end],
                "ts": idx[ke:end],
                # Index der M5-Bar, deren Schluss ein M15-Schluss ist (:10/:25/:40/:55)
                "m15c": (mins[ke:end] % 15) == 10,
            })


def _first(mask: np.ndarray) -> int:
    i = int(np.argmax(mask)) if mask.size else 0
    return i if mask.size and mask[i] else 10**9


def simuliere(p: Pfade, *, k=3.0, stop="touch", tp=5.0, hold=4, anchor="signal",
              tp_mode="touch", hold_mode="exact", bps=2.01, swap=SWAP_BPS_PRO_TAG) -> pd.DataFrame:
    half = bps / 10_000 / 2
    rows = []
    for it in p.items:
        t = it["t"]
        d = int(t["direction"])
        atr, trig = float(t["atr"]), float(t["trigger"])
        sl_sig = trig - d * k * atr
        # Restlaufzeit-Gate gegen den Signal-SL (close-Modus: Notfall-SL beruehrt
        # oder Fuell-Bar schliesst jenseits des SL)
        gate = sl_sig if stop == "touch" else sl_sig - d * k * atr
        if it["pre_l"].size and ((it["pre_l"] <= gate).any() if d == 1 else (it["pre_h"] >= gate).any()):
            continue
        if stop == "close" and (it["pre_c"] - sl_sig) * d < 0:
            continue
        o, h, l, c = it["o"], it["h"], it["l"], it["c"]
        entry = o[0] * (1 + d * half)
        if anchor == "signal":
            sl = sl_sig
            dist = (entry - sl) * d
            sim_dist = abs(float(t["entry_price"]) - sl_sig)
            if dist <= 0 or (sim_dist - dist) / sim_dist > MAX_CONSUMED_R:
                continue
        else:  # EK: Distanz des Signals am Live-Kurs
            dist = float(t["sim_dist"])
            sl = entry - d * dist
        hard = sl if stop == "touch" else sl - d * k * atr  # Notfall-SL bei 2k ab Trigger
        tp_px = None if tp is None else entry + d * tp * dist

        i_hard = _first(l <= hard) if d == 1 else _first(h >= hard)
        if stop == "close":
            cc = it["m15c"] & ((c < sl) if d == 1 else (c > sl))
            j = _first(cc)
            i_close = j + POLL if j < 10**9 else 10**9
        else:
            i_close = 10**9
        if tp_px is None:
            i_tp = 10**9
        elif tp_mode == "touch":
            i_tp = _first(h >= tp_px) if d == 1 else _first(l <= tp_px)
        else:  # auf M15-Schluss gepollt (heutiger Funded/FK-Stand)
            j = _first(it["m15c"] & ((c >= tp_px) if d == 1 else (c <= tp_px)))
            i_tp = j + POLL if j < 10**9 else 10**9
        n_hold = 12 * 24 * hold + (POLL if hold_mode == "polled" else 0)
        i_time = n_hold if n_hold < len(o) else len(o) - 1

        i = min(i_hard, i_close, i_tp, i_time)
        i = min(i, len(o) - 1)
        if i == i_hard:
            raw = min(o[i], hard) if d == 1 else max(o[i], hard)
            grund = "sl"
        elif i == i_tp and tp_mode == "touch":
            raw = max(o[i], tp_px) if d == 1 else min(o[i], tp_px)  # Gap nach vorn zaehlt mit
            grund = "tp"
        else:
            raw = o[i]
            grund = "close_sl" if i == i_close else ("tp" if i == i_tp else "zeit")
        tage = max(1, int(np.ceil((it["ts"][i] - it["ts"][0]) / pd.Timedelta(days=1)))) \
            if (it["ts"][i] - it["ts"][0]) > pd.Timedelta(hours=2) else 0
        kosten = raw * half + entry * swap / 10_000 * tage
        r = (d * (raw - entry) - kosten) / dist
        rows.append({"et": t["et"], "xt": it["ts"][i], "jahr": t["et"].year, "r": r, "grund": grund})
    df = pd.DataFrame(rows)
    return deckel(df, REV_MAX_CONCURRENT)


def deckel(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if df.empty:
        return df
    offen, keep = [], []
    for i, row in df.sort_values("et").iterrows():
        offen = [x for x in offen if x > row["et"]]
        if len(offen) >= n:
            continue
        offen.append(row["xt"])
        keep.append(i)
    return df.loc[keep].sort_values("et").reset_index(drop=True)


def kennzahlen(df: pd.DataFrame) -> dict:
    r = df["r"]
    w, l = r[r > 0], r[r <= 0]
    eq = df.sort_values("xt")["r"].cumsum().to_numpy()
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min()) if len(eq) else 0.0
    daily = (df.set_index("xt")["r"] * RISK).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    sh = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else float("nan")
    return {"n": int(len(r)), "avg_r": float(r.mean()), "sum_r": float(r.sum()),
            "pf": float(w.sum() / abs(l.sum())) if l.sum() else float("nan"),
            "hit": float((r > 0).mean()), "maxdd_r": dd, "sharpe": sh,
            "ret_dd": float(r.sum() / abs(dd)) if dd else float("nan"),
            "pos_jahre": int((df.groupby("jahr")["r"].sum() > 0).sum()),
            "jahre": int(df["jahr"].nunique())}


def mc(df: pd.DataFrame) -> dict:
    daily = (df.set_index("xt")["r"] * RISK).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    s = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)["summary"]
    dd = np.asarray(s["max_drawdown_pct"])
    return {"mc_med_dd": float(np.median(dd)), "mc_p_dd6": float((np.abs(dd) > 6).mean()),
            "mc_med_ret": float(np.median(s["total_return_pct"]))}


def walk_forward(res: dict, base_key, score: str) -> dict:
    jahre = sorted({j for df in res.values() for j in df["jahr"].unique()})
    oos, base, picks = [], [], []
    for y in jahre[3:]:  # mind. 3 Jahre In-Sample
        best, best_s = None, -np.inf
        for key, df in res.items():
            is_ = df[df["jahr"] < y]
            if len(is_) < 40:
                continue
            kz = kennzahlen(is_)
            s = kz["sum_r"] if score == "sum_r" else kz["ret_dd"]
            if s > best_s:
                best, best_s = key, s
        picks.append((y, best))
        oos.append(res[best][res[best]["jahr"] == y])
        base.append(res[base_key][res[base_key]["jahr"] == y])
    o, b = pd.concat(oos), pd.concat(base)
    besser = sum(1 for (y, _), x, z in zip(picks, oos, base) if x["r"].sum() > z["r"].sum())
    return {"score": score, "oos": kennzahlen(o), "baseline": kennzahlen(b),
            "jahre_besser": besser, "jahre": len(picks),
            "picks": [(y, str(k)) for y, k in picks]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--alle-signale", action="store_true")
    args = ap.parse_args()
    global ALLE_SIGNALE
    ALLE_SIGNALE = args.alle_signale
    bars, rib, sig = lade(args.cache)
    tr = kandidaten(rib, sig)
    p = Pfade(tr, bars["m5"])
    print(f"Kandidaten {len(tr)}, modellierbar {len(p.items)}")

    ref = {
        "live_funded": dict(k=3.0, stop="touch", tp=5.0, hold=4, tp_mode="polled", hold_mode="polled"),
        "live_ek": dict(k=3.0, stop="touch", tp=5.0, hold=10, anchor="ek"),
    }
    res, kz = {}, {}
    for name, kw in ref.items():
        res[name] = simuliere(p, **kw)
        kz[name] = kennzahlen(res[name])
    for k, st, tp, hd in itertools.product(K_GRID, STOP_GRID, TP_GRID, HOLD_GRID):
        key = (k, st, tp, hd)
        res[key] = simuliere(p, k=k, stop=st, tp=tp, hold=hd)
        kz[key] = kennzahlen(res[key])

    tab = pd.DataFrame(kz).T
    tab.index = [str(i) for i in tab.index]
    print("\nReferenzen:")
    print(tab.loc[["live_funded", "live_ek"]].round(3).to_string())
    print("\nTop 20 nach Return/MaxDD (min. 150 Trades):")
    top = tab[tab["n"] >= 150].sort_values("ret_dd", ascending=False).head(20)
    print(top.round(3).to_string())
    print("\nTop 10 nach Sharpe:")
    print(tab[tab["n"] >= 150].sort_values("sharpe", ascending=False).head(10).round(3).to_string())

    # Randeffekte (Mittel ueber das restliche Grid)
    grid = tab.drop(index=["live_funded", "live_ek"]).copy()
    parts = [eval(i) for i in grid.index]
    for pos, name in enumerate(["k", "stop", "tp", "hold"]):
        grid[name] = [str(x[pos]) for x in parts]
    print("\nRandeffekte (Mittel Sharpe / Return-DD ueber das restliche Grid):")
    for name in ["k", "stop", "tp", "hold"]:
        print(grid.groupby(name)[["sharpe", "ret_dd", "avg_r", "sum_r"]].mean().round(3).to_string(), "\n")

    wf = {s: walk_forward({k: v for k, v in res.items() if k != "live_ek"}, "live_funded", s)
          for s in ("sum_r", "ret_dd")}
    for s, w in wf.items():
        print(f"\nWalk-Forward (IS-Kriterium {s}): OOS {w['oos']['sum_r']:.1f} R / DD {w['oos']['maxdd_r']:.1f} "
              f"gegen live_funded {w['baseline']['sum_r']:.1f} / {w['baseline']['maxdd_r']:.1f}; "
              f"besser in {w['jahre_besser']}/{w['jahre']} Jahren")
        print("   picks:", w["picks"])

    out = {"tabelle": tab.round(4).to_dict(orient="index"), "walk_forward": wf}
    kandid = list(top.index[:8]) + ["live_funded", "live_ek"]
    out["mc"] = {}
    out["sensitiv"] = {}
    print("\nMonte Carlo + Sensitivitaet (IQ-Kosten, Swap 0, Versatz 30 Min.):")
    for key in kandid:
        rk = key if key in res else eval(key)
        m = mc(res[rk])
        out["mc"][key] = m
        if isinstance(rk, tuple):
            kw = dict(k=rk[0], stop=rk[1], tp=rk[2], hold=rk[3])
        else:
            kw = ref[rk]
        iq = kennzahlen(simuliere(p, **kw, bps=KOSTEN["iq"]))
        sw0 = kennzahlen(simuliere(p, **kw, swap=0.0))
        out["sensitiv"][key] = {"iq": iq, "swap0": sw0}
        print(f"  {key:<32} MC-MedDD {m['mc_med_dd']:6.2f}% P(DD>6%) {m['mc_p_dd6']:.2f} "
              f"MC-Ret {m['mc_med_ret']:6.1f}% | IQ Sharpe {iq['sharpe']:.2f} SumR {iq['sum_r']:.0f} | "
              f"Swap0 Sharpe {sw0['sharpe']:.2f}")

    # Jahresreihe fuer die Top 3 + live
    jr = {key: (res[key if key in res else eval(key)].groupby("jahr")["r"].sum().round(1))
          for key in list(top.index[:3]) + ["live_funded", "live_ek"]}
    print("\nSum R je Jahr:")
    print(pd.DataFrame(jr).to_string())
    out["jahre"] = {k: v.to_dict() for k, v in jr.items()}

    dest = REPO_DIR / "knowledge" / "_data" / ("ctnl_exit_optimierung" + ("_alle" if ALLE_SIGNALE else "") + ".json")
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {dest}")


if __name__ == "__main__":
    main()
