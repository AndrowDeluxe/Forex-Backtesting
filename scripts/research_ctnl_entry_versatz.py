"""CTNL-Reversal: Edge in Abhaengigkeit vom Einstiegsversatz, minutengenau
auf M5 (2026-10-03, Nutzerauftrag "Backteste den zeitlichen Versatz bei den
Orders im Vergleich zum eigentlichen Edge aus dem Backtest").

Ausloeser: am 2026-10-02 stieg EK um 12:59 UTC ein, Funded/FK erst 13:13
(gleiches Signal, Signalbar 12:30 UTC). Gemessen an allen echten Fills in den
State-Dateien liegen Funded/FK seit dem 17.09. konstant 28 Min. hinter dem
Backtest-Fill (open der Bar Signalbar+1), EK 14 Min.

Ursache Funded/FK: _scan_ctnl() erzeugt einen Trade erst, wenn die
FUELL-Bar (Signalbar+1) geschlossen im Lake liegt (simulate_trades_
concurrent laeuft nur bis n-1), EK liest das Signal direkt von der
Signalbar (live_signal.reversal_signal).

Achtung Anker: alle frueheren CTNL-Rechnungen (research_ctnl_optimization.
to_live, REAL_LAG=1) setzten Lag 1 (15 Min.) als realen Betriebspunkt. Das
ist EKs Takt. Funded/FK liefen bei ~Lag 2 (28 Min.).

Zwei Ausfuehrungslogiken, beide auf denselben Signalen (ribbon-konform,
Spike >= 0,75 ATR, Kappung REV_MAX_CONCURRENT -- die Live-Konfiguration):

  funded  absoluter Signal-SL als Broker-Stop (Beruehrung auf M5), kein
          Broker-TP, Exit sonst zum Exit der Simulation (Schlusskurs der
          M15-Exit-Bar); R-Detektor 0,50R; Restlaufzeit-Gate.
  ek      SL-DISTANZ des Signals am Live-Kurs neu verankert, Broker-TP 5R
          (beides Beruehrung auf M5, beide in derselben Bar -> SL,
          konservativ), kein Zeit-Exit; Restlaufzeit-Gate gegen Signal-SL.

R je Trade = Ergebnis / tatsaechlich riskierte Distanz (so sizen die Bridges).
Kosten: MEASURED_BPS (TTP, teuerster Broker) Round-Trip, je Haelfte.

Aufruf: python scripts/research_ctnl_entry_versatz.py [--cache <pkl>]
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
sys.path[:0] = [str(REPO_DIR), str(REPO_DIR / "scripts")]

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT, REV_TP_R  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from gold_smc_htf_ltf.spike_gate import SPIKE_MIN_ATR  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive, load_bars, stop_level  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS  # noqa: E402
from research_ctnl_ribbon_both_legs import ribbon_direction, stats  # noqa: E402
from strategy.backtest import BacktestConfig  # noqa: E402

VERSATZ_MIN = [0, 5, 10, 15, 20, 25, 30, 45, 60]
MAX_CONSUMED_R = 0.50
EK_MAX_HALTE_M5 = 12 * 24 * 10  # 10 Tage Sicherheitsgrenze, EK hat keinen Zeit-Exit


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


def signale(rib, sig) -> pd.DataFrame:
    cfg = BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False,
                         take_profit_r=REV_TP_R, max_hold_bars=96 * 4)
    tr = _cap_concurrent(simulate_trades_concurrent(sig, cfg), REV_MAX_CONCURRENT)
    row = sig.iloc[tr["signal_bar"].to_numpy()]
    tr = tr.assign(spike=((row["high"] - row["low"]) / row["atr"]).to_numpy())
    tr["et"] = _utc_naive(tr["entry_time"])
    tr["xt"] = _utc_naive(tr["exit_time"])
    tr["rib"] = rib.reindex(tr["et"], method="ffill").to_numpy()
    konform = ((tr["direction"] == 1) & (tr["rib"] > 0)) | ((tr["direction"] == -1) & (tr["rib"] < 0))
    tr = tr[konform & (tr["spike"] >= SPIKE_MIN_ATR)]
    return tr.sort_values("et").reset_index(drop=True)


def replay(tr: pd.DataFrame, m5: pd.DataFrame, versatz: int, logik: str) -> pd.DataFrame:
    idx = _utc_naive(m5.index)
    op, hi, lo, cl = (m5[c].to_numpy() for c in ("open", "high", "low", "close"))
    half = MEASURED_BPS / 10_000 / 2
    rows = []
    for _, t in tr.iterrows():
        d = int(t["direction"])
        sl_sig = stop_level(t)
        dist = float(t["initial_risk"])
        if dist <= 0:
            continue
        t_fill = t["et"]                              # Backtest-Fill: open der Bar Signalbar+1
        t_entry = t_fill + pd.Timedelta(minutes=versatz)
        t_sim_exit = t["xt"] + pd.Timedelta(minutes=15)  # Exit am Schluss der M15-Exit-Bar
        k0 = idx.searchsorted(t_fill)
        k = idx.searchsorted(t_entry)
        if k >= len(op):
            continue
        basis = {"et": t_fill, "jahr": t_fill.year, "direction": d}

        if t_entry >= t_sim_exit and logik == "funded":
            rows.append({**basis, "status": "schon_geschlossen"})
            continue
        # Restlaufzeit-Gate: Signal-SL zwischen Backtest-Fill und Live-Entry beruehrt?
        if k > k0:
            seg = slice(k0, k)
            if (lo[seg] <= sl_sig).any() if d == 1 else (hi[seg] >= sl_sig).any():
                rows.append({**basis, "status": "schon_gestoppt"})
                continue

        entry = op[k] * (1 + d * half)
        if logik == "funded":
            eff = (entry - sl_sig) * d
            if eff <= 0 or (dist - eff) / dist > MAX_CONSUMED_R:
                rows.append({**basis, "status": "r_detektor"})
                continue
            k_end = idx.searchsorted(t_sim_exit)  # erste M5-Bar NACH dem Sim-Exit
            seg_lo, seg_hi = lo[k:k_end], hi[k:k_end]
            hit = np.flatnonzero(seg_lo <= sl_sig) if d == 1 else np.flatnonzero(seg_hi >= sl_sig)
            if hit.size:
                raw_exit = min(op[k + hit[0]], sl_sig) if d == 1 else max(op[k + hit[0]], sl_sig)
                grund = "sl"
            else:
                raw_exit = cl[k_end - 1]
                grund = str(t["exit_reason"])
            risiko = eff
        else:  # ek
            sl = entry - d * dist
            tp = entry + d * REV_TP_R * dist
            k_end = min(len(op), k + EK_MAX_HALTE_M5)
            seg_lo, seg_hi = lo[k:k_end], hi[k:k_end]
            sl_hit = np.flatnonzero(seg_lo <= sl) if d == 1 else np.flatnonzero(seg_hi >= sl)
            tp_hit = np.flatnonzero(seg_hi >= tp) if d == 1 else np.flatnonzero(seg_lo <= tp)
            i_sl = sl_hit[0] if sl_hit.size else np.inf
            i_tp = tp_hit[0] if tp_hit.size else np.inf
            if i_sl <= i_tp and np.isfinite(i_sl):
                j = k + int(i_sl)
                raw_exit = min(op[j], sl) if d == 1 else max(op[j], sl)
                grund = "sl"
            elif np.isfinite(i_tp):
                raw_exit, grund = tp, "tp"
            else:
                raw_exit, grund = cl[k_end - 1], "zeit"
            risiko = dist
        exit_px = raw_exit * (1 - d * half)
        rows.append({**basis, "status": "genommen", "grund": grund,
                     "entry": entry, "r": d * (exit_px - entry) / risiko})
    return pd.DataFrame(rows)


def backtest_referenz(tr: pd.DataFrame) -> dict:
    """Der 'eigentliche Edge': Fill zum Backtest-Preis, Exit der Simulation."""
    return stats(tr["r_multiple"])


def bootstrap_diff(a: pd.DataFrame, b: pd.DataFrame, n: int = 5000, seed: int = 7) -> dict:
    """Gepaarter Vergleich Ø R (b - a) auf Trades, die in BEIDEN genommen wurden,
    plus der Effekt der unterschiedlich verpassten Trades ueber Summe R."""
    ga = a[a["status"] == "genommen"].set_index("et")["r"]
    gb = b[b["status"] == "genommen"].set_index("et")["r"]
    both = ga.index.intersection(gb.index)
    diff = (gb.loc[both] - ga.loc[both]).to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([rng.choice(diff, diff.size).mean() for _ in range(n)])
    return {"gepaart_n": int(both.size), "diff_avg_r": float(diff.mean()),
            "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "summe_r_a": float(ga.sum()), "summe_r_b": float(gb.sum())}


def zeile(df: pd.DataFrame) -> dict:
    g = df[df["status"] == "genommen"]
    s = stats(g["r"])
    s.update({f"n_{k}": int(v) for k, v in df["status"].value_counts().items() if k != "genommen"})
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=None)
    args = ap.parse_args()
    bars, rib, sig = daten(args.cache)
    tr = signale(rib, sig)
    m5 = bars["m5"]
    print(f"Signale (ribbon-konform, Spike>={SPIKE_MIN_ATR}): {len(tr)}  "
          f"{tr['et'].min():%Y-%m-%d} .. {tr['et'].max():%Y-%m-%d}; M5 ab {_utc_naive(m5.index).min():%Y-%m-%d}")
    ref = backtest_referenz(tr)
    print(f"Backtest-Referenz (Fill = open Signalbar+1, Sim-Exit): {ref}")

    out = {"referenz": ref, "kosten_bps": MEASURED_BPS, "n_signale": int(len(tr)), "logiken": {}}
    replays = {}
    for logik in ("funded", "ek"):
        out["logiken"][logik] = {}
        print(f"\n== {logik} ==")
        print(f"{'Versatz':>8} {'n':>4} {'avgR':>7} {'SumR':>7} {'PF':>5} {'Hit':>5}  verpasst")
        for v in VERSATZ_MIN:
            rep = replay(tr, m5, v, logik)
            replays[(logik, v)] = rep
            z = zeile(rep)
            out["logiken"][logik][v] = z
            verp = {k: z[k] for k in z if k.startswith("n_")}
            print(f"{v:>6}m {z['trades']:>4} {z['avg_r']:>7.3f} {z['summe_r']:>7.1f} "
                  f"{z['profit_factor']:>5.2f} {z['trefferquote']:>5.2f}  {verp}")

    vergl = {
        "funded_30_vs_15": bootstrap_diff(replays[("funded", 30)], replays[("funded", 15)]),
        "funded_30_vs_5": bootstrap_diff(replays[("funded", 30)], replays[("funded", 5)]),
        "ek15_vs_funded15": bootstrap_diff(replays[("funded", 15)], replays[("ek", 15)]),
    }
    out["vergleiche"] = vergl
    print("\nGepaarte Vergleiche (b - a):")
    for k, v in vergl.items():
        print(f"  {k}: {v}")

    # Jahresweise: Funded heute (30) gegen EK-Takt (15) gegen schnell (5)
    jahre = {}
    for v in (5, 15, 30):
        g = replays[("funded", v)]
        g = g[g["status"] == "genommen"]
        jahre[v] = g.groupby("jahr")["r"].sum().round(1).to_dict()
    out["jahre_summe_r_funded"] = jahre
    print("\nSumme R je Jahr (funded-Logik):")
    print(pd.DataFrame(jahre).to_string())

    dest = REPO_DIR / "knowledge" / "_data" / "ctnl_entry_versatz.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {dest}")


if __name__ == "__main__":
    main()
