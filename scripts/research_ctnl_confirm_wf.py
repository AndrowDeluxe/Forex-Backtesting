"""CTNL-Reversal: Spike-Filter + Risikohalbierung + Kill-Switch-Varianten,
Walk-Forward und Monte Carlo (2026-09-30, Befund 19).

Baut auf Befund 18 auf (`research_ctnl_confirmations.py`), rechnet aber am
realen Betriebspunkt (`to_live`: Lag + R-Detektor) und NUR auf dem
ribbon-konformen Set (live seit 2026-09-30).

OHNE LOOKAHEAD: Serien, Kill-Switches und Tages-/Wochenverluste sehen nur
Trades, deren exit_time <= entry_time des neuen Trades liegt -- so wie live.

Aufruf: python scripts/research_ctnl_confirm_wf.py [--cache <pkl>]
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_DIR), str(REPO_DIR / "scripts"), str(REPO_DIR / "ou_paper_backtest")]

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import ribbon_direction, stats  # noqa: E402
from strategy.backtest import BacktestConfig  # noqa: E402

RISK = 0.0015  # FK_RISK_REV


def daten(cache: Path | None):
    if cache and cache.exists():
        d = pickle.load(open(cache, "rb"))
        return d["bars"], d["rib"], d["sig"]
    S, E = "2016-01-01", pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    bars = load_bars(S, E)
    rib = ribbon_direction(bars["h4"], fetch_gold_d1(S, E), fetch_gold_w1(S, E))
    sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)
    if cache:
        pickle.dump({"bars": bars, "rib": rib, "sig": sig}, open(cache, "wb"))
    return bars, rib, sig


def trades(bars, rib, sig) -> pd.DataFrame:
    cfg = BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False,
                         take_profit_r=5.0, max_hold_bars=96 * 4)
    tr = _cap_concurrent(simulate_trades_concurrent(sig, cfg), REV_MAX_CONCURRENT)
    # Merkmal der Signalbar VOR dem Lag-Replay anhaengen (signal_bar = Positionsindex in sig)
    row = sig.iloc[tr["signal_bar"].to_numpy()]
    tr = tr.assign(spike=((row["high"] - row["low"]) / row["atr"]).to_numpy())
    rep = to_live(tr, bars["m15"]).copy()
    if "spike" not in rep.columns:
        rep = rep.merge(tr[["entry_time", "spike"]], on="entry_time", how="left")
    et = _utc_naive(rep["entry_time"])
    rep["et"] = et
    rep["xt"] = _utc_naive(rep["exit_time"])
    rep["rib"] = rib.reindex(et, method="ffill").to_numpy()
    rep = rep[((rep["direction"] == 1) & (rep["rib"] > 0)) | ((rep["direction"] == -1) & (rep["rib"] < 0))]
    return rep.sort_values("et").reset_index(drop=True)


def gewichte(d: pd.DataFrame, *, spike: float = 0.0, half_n: int | None = None,
             dd_kill: float | None = None, day_stop: float | None = None,
             week_stop: float | None = None) -> np.ndarray:
    """Positionsgroesse je Trade (0 = nicht genommen, 0.5 = halbes Risiko).
    Alle Zustaende nur aus Trades mit exit_time <= entry_time."""
    et, xt, r = d["et"].to_numpy(), d["xt"].to_numpy(), d["r"].to_numpy()
    sp = d["spike"].to_numpy()
    w = np.zeros(len(d))
    exit_order = np.argsort(xt, kind="stable")
    kill = False
    for i in range(len(d)):
        closed = exit_order[xt[exit_order] <= et[i]]
        # Schatten-Kurve ueber ALLE Signale (wie live: der Scan simuliert weiter)
        if dd_kill is not None:
            c = np.cumsum(r[closed]) if len(closed) else np.array([0.0])
            ddr = c[-1] - max(0.0, c.max())
            if not kill and ddr <= -dd_kill:
                kill = True
            elif kill and ddr >= -dd_kill / 2:
                kill = False
            if kill:
                continue
        if sp[i] < spike:
            continue
        m = 1.0
        if half_n is not None:
            streak = 0
            for j in closed[::-1]:          # juengster geschlossener zuerst
                if r[j] > 0:
                    break
                streak += 1
            if streak >= half_n:
                m = 0.5
        if day_stop is not None or week_stop is not None:
            taken = closed[w[closed] > 0]
            real = r[taken] * w[taken]
            tday = pd.Timestamp(et[i]).normalize()
            if day_stop is not None:
                if real[pd.DatetimeIndex(xt[taken]).normalize() == tday].sum() <= -day_stop:
                    continue
            if week_stop is not None:
                wk = tday - pd.Timedelta(days=tday.dayofweek)
                if real[pd.DatetimeIndex(xt[taken]) >= wk].sum() <= -week_stop:
                    continue
        w[i] = m
    return w


def kennzahlen(d: pd.DataFrame, w: np.ndarray) -> dict:
    x = d.assign(rw=d["r"] * w)
    x = x[w > 0]
    c = np.cumsum(x["rw"].to_numpy())
    dd = float((c - np.maximum.accumulate(np.r_[0, c])[1:]).min()) if len(c) else 0.0
    daily = (x.set_index("et")["rw"] * RISK).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    m = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = m["summary"] if isinstance(m, dict) and "summary" in m else m
    jahre = x.groupby(x["et"].dt.year)["rw"].sum()
    return {"trades": int(len(x)), "summe_r": float(x["rw"].sum()), "maxdd_r": dd,
            "ret_dd": float(x["rw"].sum() / -dd) if dd < 0 else float("nan"),
            "jahre_positiv": f"{int((jahre > 0).sum())}/{len(jahre)}",
            "mc_med_dd_pct": float(np.median(s["max_drawdown_pct"])),
            "mc_p_dd_6": float((np.abs(s["max_drawdown_pct"]) > 6).mean()),
            "mc_p_dd_4": float((np.abs(s["max_drawdown_pct"]) > 4).mean()),
            "mc_ret_pct": float(np.median(s["total_return_pct"])),
            "mc_sharpe": float(np.median(s["sharpe"]))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=REPO_DIR / "knowledge" / "_data" / "ctnl_confirm_wf.json")
    a = ap.parse_args()
    d = trades(*daten(a.cache))
    d["jahr"] = d["et"].dt.year
    print(f"ribbon-konform, live-Betriebspunkt: {len(d)} Trades, ΣR {d['r'].sum():+.1f}")

    varianten = {"heute": {}}
    for s in (0.5, 0.6, 0.75, 0.9):
        varianten[f"spike{s}"] = {"spike": s}
    for n in (2, 3, 4, 5):
        varianten[f"half{n}"] = {"half_n": n}
    for s in (0.6, 0.75):
        for n in (3, 4):
            varianten[f"spike{s}+half{n}"] = {"spike": s, "half_n": n}
    for k in (44, 20, 10):
        varianten[f"ddkill{k}R"] = {"dd_kill": k}
    for x in (3, 4):
        varianten[f"tagesstopp{x}R"] = {"day_stop": x}
    for x in (5, 8):
        varianten[f"wochenstopp{x}R"] = {"week_stop": x}
    varianten["spike0.75+half3+ddkill20R"] = {"spike": 0.75, "half_n": 3, "dd_kill": 20}

    res, gew = {}, {}
    print(f"\n  {'Variante':>28} {'n':>5} {'ΣR':>7} {'MaxDD':>7} {'R/DD':>5} {'J+':>6} "
          f"{'MC-MedDD':>9} {'P>4%':>6} {'P>6%':>6} {'Ret':>7} {'Sharpe':>6}")
    for name, kw in varianten.items():
        w = gewichte(d, **kw)
        gew[name] = w
        k = kennzahlen(d, w)
        res[name] = k
        print(f"  {name:>28} {k['trades']:>5} {k['summe_r']:>+7.1f} {k['maxdd_r']:>+7.1f} {k['ret_dd']:>5.1f} "
              f"{k['jahre_positiv']:>6} {k['mc_med_dd_pct']:>8.2f}% {k['mc_p_dd_4']:>6.1%} "
              f"{k['mc_p_dd_6']:>6.1%} {k['mc_ret_pct']:>6.1f}% {k['mc_sharpe']:>6.2f}")

    # Walk-Forward je Familie: waehlt je Jahr den IS-besten Parameter, Baseline = heute
    def rep(name):
        w = gew[name]
        return d.assign(r=d["r"] * w)[w > 0][["jahr", "r"]]
    wf = {}
    for fam, keys in {"spike": ["heute"] + [k for k in varianten if k.startswith("spike") and "+" not in k],
                      "half": ["heute"] + [k for k in varianten if k.startswith("half")],
                      "kombi": ["heute"] + [k for k in varianten if "+" in k],
                      "killswitch": ["heute"] + [k for k in varianten if "kill" in k or "stopp" in k]}.items():
        wf[fam] = anchored_walk_forward({k: rep(k) for k in keys}, "heute", f"ctnl_reversal: {fam}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"varianten": res, "walkforward": wf}, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
