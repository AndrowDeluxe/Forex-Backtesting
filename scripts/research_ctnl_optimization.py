"""CTNL Edge: Optimierung von TP, Regime-Filter und Signal-Parametern (2026-09-23)

Nutzerauftrag nach der Diagnose (knowledge/projects/ctnl-kostenvalidierung.md
Befund 7): TP-Sweep, Regime-Filter, Signal-Parameter -- beide Beine.

WARUM DIESES SKRIPT ANDERS GEBAUT IST ALS EIN UEBLICHER SWEEP
Ein Sweep, der auf der Gesamthistorie den besten Parameter sucht, findet immer
einen. Die Frage ist nicht "welcher Wert war rueckblickend am besten", sondern
"haette die AUSWAHLPROZEDUR mir in der Praxis geholfen". Deshalb:

  ANKER-WALK-FORWARD. Fuer jedes Auswertungsjahr Y:
    - waehle den Parameter auf ALLEN Trades vor dem 01.01.Y (in-sample),
    - werte ihn auf Jahr Y aus (out-of-sample, zum Wahlzeitpunkt ungesehen),
    - ruecke ein Jahr weiter.
  Die Summe dieser OOS-Jahre ist das Ergebnis der Prozedur. Sie wird gegen
  die GESPERRTE Baseline auf denselben Jahren gehalten. Nur wenn die Prozedur
  die Baseline out-of-sample schlaegt, ist der Parameter ein Hebel und kein
  Rueckspiegel.

  Zusaetzlich wird die PARAMETERFLAECHE ueber die Gesamthistorie ausgewiesen.
  Ein Optimum auf einem Grat ist keins -- flach ist besser als hoch.

  Der OU-Fall ist die Mahnung: dort war "BE-Stop aus" IS-Sieger ALLER 54
  Kombinationen und drehte das OOS-Vorzeichen (siehe
  knowledge/projects/ou-modell-kostenvalidierung.md).

REGIME-FILTER: FESTE SCHWELLE, KEIN EXPANDIERENDES QUANTIL
Die Schwelle wird im IS-Fenster als Quantil bestimmt und dann als ABSOLUTER
Wert ins OOS uebernommen. Ein mitlaufendes Quantil waere zwar bequemer, macht
den Filter aber nicht reproduzierbar -- ein Trade kann beim Nachrechnen
kippen, obwohl sich nichts geaendert hat (Fund gold_asb, siehe Memory
`gold_asb_liquidity_filter_reproducibility`). Fuer ein Bein, das live Geld
bewegt, ist Reproduzierbarkeit nicht verhandelbar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation  # noqa: E402
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from research_ctnl_execution_costs import (  # noqa: E402
    CONT_CFG,
    REV_CFG,
    _cap_concurrent,
    _utc_naive,
    load_bars,
    replay_with_lag,
)
from strategy.backtest import BacktestConfig, simulate_trades  # noqa: E402

sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))
from monte_carlo import run_monte_carlo  # noqa: E402  -- etablierter Pfad, siehe research_gold_smc_phase6_robustness.py

MEASURED_BPS = 2.01     # TTP, der teuerste der vier Broker (konservativ)
REAL_LAG = 1            # realer Betriebspunkt, siehe Befund 1
MAX_CONSUMED_R = 0.50   # R-Detektor der Bridges
OOS_YEARS = list(range(2019, 2027))   # ab 2019: davor zu wenig IS-Historie
MIN_IS_TRADES = 120     # darunter wird nicht gewaehlt, sondern die Baseline gefahren


# --------------------------------------------------------------- Kennzahlen


def stats(r: pd.Series) -> dict:
    r = pd.Series(r).dropna()
    if r.empty:
        return {"trades": 0, "avg_r": float("nan"), "summe_r": 0.0,
                "profit_factor": float("nan"), "trefferquote": float("nan")}
    w, l = r[r > 0], r[r <= 0]
    return {
        "trades": int(len(r)),
        "avg_r": float(r.mean()),
        "summe_r": float(r.sum()),
        "trefferquote": float((r > 0).mean()),
        "profit_factor": float(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else float("nan"),
    }


# ------------------------------------------------------ Trades je Kandidat


def leg_trades(bars: dict, leg: str, *, tp_r: float | None, sig_kwargs: dict) -> pd.DataFrame:
    """Simulierte Trades fuer eine Parametrierung. Teuer -- der Aufrufer cacht."""
    cfg_base = dict(REV_CFG if leg == "ctnl_reversal" else CONT_CFG)
    cfg_base["spread_bps"] = MEASURED_BPS
    if leg == "ctnl_reversal":
        cfg_base["take_profit_r"] = tp_r
        sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **sig_kwargs)
        tr = simulate_trades_concurrent(sig, BacktestConfig(**cfg_base))
        return _cap_concurrent(tr, REV_MAX_CONCURRENT)
    # Continuation: Ziel ist normalerweise VWAP. Ein R-Ziel ist nur dann
    # sinnvoll zu testen, wenn das VWAP-Ziel dafuer abgeschaltet wird --
    # sonst gewinnt schlicht das zuerst erreichte und der Test misst nichts.
    if tp_r is not None:
        cfg_base["use_vwap_target"] = False
        cfg_base["take_profit_r"] = tp_r
    sig = run_continuation(bars["h4"], bars["h1"], bars["m5"], trend_df=bars["m15"], **sig_kwargs)
    return simulate_trades(sig, BacktestConfig(**cfg_base))


def to_live(tr: pd.DataFrame, bar_df: pd.DataFrame) -> pd.DataFrame:
    """Auf den realen Betriebspunkt umrechnen: Lag 1 + R-Detektor."""
    if tr.empty:
        return tr
    rep = replay_with_lag(tr, bar_df, REAL_LAG, MEASURED_BPS / 10_000.0)
    rep = rep[(rep["effective_risk"] > 0) & (rep["consumed_r"] <= MAX_CONSUMED_R)].copy()
    rep["jahr"] = _utc_naive(rep["entry_time"]).dt.year
    return rep


# ------------------------------------------------------------ Regime-Filter


def regime_feature(bars: pd.DataFrame, window: int = 100) -> pd.Series:
    """Efficiency Ratio: |Nettobewegung| / Summe der Absolutbewegungen.

    Nahe 1 = sauberer Trend, nahe 0 = richtungsloses Hin und Her. Die Diagnose
    (Befund 7e) fand das Reversal-Bein in den UNTEREN Quartilen am besten --
    strategiekonform, ein Reversal-Setup lebt von Richtungslosigkeit.
    Ausschliesslich rueckwaertsgerichtet, also zum Einstieg verfuegbar.
    """
    idx = _utc_naive(bars.index)
    px = pd.Series(bars["close"].to_numpy(), index=idx)
    return (px.diff(window).abs() / px.diff().abs().rolling(window).sum())


def attach_feature(rep: pd.DataFrame, feat: pd.Series) -> pd.DataFrame:
    rep = rep.copy()
    rep["feat"] = feat.reindex(_utc_naive(rep["entry_time"])).to_numpy()
    return rep


# ------------------------------------------------------- Anker-Walk-Forward


def anchored_walk_forward(rep_by_param: dict, baseline_key, label: str) -> dict:
    """rep_by_param: {parameterwert: DataFrame mit Spalten 'jahr','r'}.

    Waehlt je Jahr den IS-besten Parameter (nach Summe R) und wertet ihn OOS aus.
    """
    params = list(rep_by_param)
    rows, oos_r, base_r, picks = [], [], [], []

    for y in OOS_YEARS:
        is_scores = {}
        for p in params:
            d = rep_by_param[p]
            s = d[d["jahr"] < y]
            if len(s) >= MIN_IS_TRADES:
                is_scores[p] = s["r"].sum()
        if not is_scores:
            continue
        pick = max(is_scores, key=is_scores.get)
        oos = rep_by_param[pick]
        oos = oos[oos["jahr"] == y]["r"]
        bas = rep_by_param[baseline_key]
        bas = bas[bas["jahr"] == y]["r"]
        rows.append({"jahr": y, "gewaehlt": pick, "oos_trades": int(len(oos)),
                     "oos_summe_r": float(oos.sum()), "baseline_summe_r": float(bas.sum()),
                     "differenz": float(oos.sum() - bas.sum())})
        oos_r.append(oos)
        base_r.append(bas)
        picks.append(pick)

    all_oos = pd.concat(oos_r) if oos_r else pd.Series(dtype=float)
    all_base = pd.concat(base_r) if base_r else pd.Series(dtype=float)
    print(f"\n  Anker-Walk-Forward -- {label}")
    print(f"    {'Jahr':>6} {'gewaehlt':>10} {'OOS n':>7} {'OOS ΣR':>9} {'Baseline ΣR':>12} {'Diff':>8}")
    for r in rows:
        print(f"    {r['jahr']:>6} {str(r['gewaehlt']):>10} {r['oos_trades']:>7} "
              f"{r['oos_summe_r']:>+9.1f} {r['baseline_summe_r']:>+12.1f} {r['differenz']:>+8.1f}")
    so, sb = stats(all_oos), stats(all_base)
    print(f"    {'GESAMT':>6} {'':>10} {so['trades']:>7} {so['summe_r']:>+9.1f} "
          f"{sb['summe_r']:>+12.1f} {so['summe_r']-sb['summe_r']:>+8.1f}")
    besser = sum(1 for r in rows if r["differenz"] > 0)
    print(f"    Prozedur schlaegt die Baseline in {besser} von {len(rows)} Jahren | "
          f"Ø R {so['avg_r']:+.3f} vs. {sb['avg_r']:+.3f} | PF {so['profit_factor']:.2f} vs. {sb['profit_factor']:.2f}")
    if so["summe_r"] <= sb["summe_r"]:
        print(f"    -> VERWORFEN: die Auswahl bringt out-of-sample nichts.")
    return {"je_jahr": rows, "oos": so, "baseline": sb,
            "jahre_besser": besser, "jahre_gesamt": len(rows),
            "gewaehlte_parameter": [str(p) for p in picks]}


def surface(rep_by_param: dict, label: str) -> dict:
    """Parameterflaeche ueber die Gesamthistorie -- zeigt, ob flach oder Grat."""
    print(f"\n  Parameterflaeche (GESAMTHISTORIE, in-sample -- nur zur Form, nicht zur Wahl) -- {label}")
    print(f"    {'Wert':>10} {'Trades':>7} {'ØR':>8} {'ΣR':>9} {'PF':>6} {'Treffer':>8}")
    out = {}
    for p, d in rep_by_param.items():
        s = stats(d["r"])
        out[str(p)] = s
        print(f"    {str(p):>10} {s['trades']:>7} {s['avg_r']:>+8.3f} {s['summe_r']:>+9.1f} "
              f"{s['profit_factor']:>6.2f} {s['trefferquote']:>7.1%}")
    return out


# ----------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    ap.add_argument("--legs", default="ctnl_reversal,ctnl_continuation")
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_optimization.json")
    args = ap.parse_args()

    print(f"Lade Gold-Bars {args.start} .. {args.end} ...")
    bars = load_bars(args.start, args.end)
    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    base_kwargs = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    base_tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    result: dict = {"measured_bps": MEASURED_BPS, "lag": REAL_LAG, "beine": {}}

    for leg in [x.strip() for x in args.legs.split(",") if x.strip()]:
        print(f"\n{'='*78}\n{leg}\n{'='*78}")
        res: dict = {}

        # ---------------- A) TP-Sweep
        # Nach oben erweitert (2026-09-23): der erste Lauf ergab eine MONOTON
        # steigende Flaeche bis zum damaligen Rand 5,0 -- ein Optimum am Rand
        # ist kein Optimum, sondern ein zu kurz gewaehlter Bereich. Die
        # MFE-Zensur aus der Diagnose (Befund 7c) verbietet nur die
        # DIAGNOSTISCHE Aussage ueber hoehere Ziele; die Simulation rechnet
        # sie problemlos, weil sie den Trade tatsaechlich weiterlaufen laesst.
        tp_values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
        if leg == "ctnl_continuation":
            tp_values = [None] + tp_values  # None = VWAP-Ziel (Baseline)
        reps = {}
        for tp in tp_values:
            tr = leg_trades(bars, leg, tp_r=tp, sig_kwargs=base_kwargs[leg])
            reps[tp] = to_live(tr, bar_src[leg])
            print(f"    TP={tp}: {len(reps[tp])} handelbare Trades")
        res["tp_flaeche"] = surface(reps, f"{leg}: take_profit_r")
        res["tp_walkforward"] = anchored_walk_forward(reps, base_tp[leg], f"{leg}: take_profit_r")

        # ---------------- B) Regime-Filter auf der Baseline-Parametrierung
        base_rep = attach_feature(reps[base_tp[leg]], regime_feature(bar_src[leg]))
        base_rep = base_rep.dropna(subset=["feat"])
        # Schwelle als IS-Quantil, dann als ABSOLUTER Wert ins OOS (siehe Docstring)
        filt = {}
        for q in (0.25, 0.40, 0.50, 0.60, 0.75, 1.00):
            thr = base_rep["feat"].quantile(q)
            d = base_rep[base_rep["feat"] <= thr].copy() if q < 1.0 else base_rep.copy()
            filt[q] = d
        res["regime_flaeche"] = surface(filt, f"{leg}: Effizienz-Quantilgrenze (1.00 = ungefiltert)")
        res["regime_walkforward"] = anchored_walk_forward(filt, 1.00, f"{leg}: Regime-Filter")

        # ---------------- C) Signal-Parameter
        if leg == "ctnl_reversal":
            variants = {
                "baseline": dict(REV_KWARGS),
                "h4_confirm_20": {**REV_KWARGS, "h4_confirm_bars": 20},
                "h4_confirm_40": {**REV_KWARGS, "h4_confirm_bars": 40},
                "h1_valid_12": {**REV_KWARGS, "h1_valid_bars": 12},
                "h1_valid_36": {**REV_KWARGS, "h1_valid_bars": 36},
                "ohne_ema_reject": {**REV_KWARGS, "require_ema_reject": False},
            }
        else:
            variants = {
                "baseline": dict(CONT_KWARGS),
                "htf_valid_12": {**CONT_KWARGS, "htf_valid_bars": 12},
                "htf_valid_36": {**CONT_KWARGS, "htf_valid_bars": 36},
                "min_target_1.0": {**CONT_KWARGS, "min_target_distance_atr": 1.0},
            }
        sig_reps = {}
        for name, kw in variants.items():
            try:
                tr = leg_trades(bars, leg, tp_r=base_tp[leg], sig_kwargs=kw)
                sig_reps[name] = to_live(tr, bar_src[leg])
                print(f"    Signal '{name}': {len(sig_reps[name])} handelbare Trades")
            except Exception as e:  # eine unzulaessige Kombination darf den Lauf nicht killen
                print(f"    Signal '{name}': uebersprungen ({type(e).__name__}: {e})")
        if len(sig_reps) > 1:
            res["signal_flaeche"] = surface(sig_reps, f"{leg}: Signal-Parameter")
            res["signal_walkforward"] = anchored_walk_forward(sig_reps, "baseline", f"{leg}: Signal-Parameter")

        # ---------------- D) Monte Carlo: Baseline gegen Regime-Filter
        # Erst hier, nachdem feststeht, WAS ueberhaupt ein Kandidat ist.
        # Risikogroesse: FK-Reversal-Split 0,15 % je Trade (live_signal.py).
        risk_pct = 0.0015 if leg == "ctnl_reversal" else 0.005
        res["monte_carlo"] = {}
        for name, d in (("baseline", filt[1.00]), ("regime_filter_q50", filt[0.50])):
            daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * risk_pct
                     ).resample("D").sum()
            daily = daily[daily.index.dayofweek < 5]
            if len(daily) < 250:
                continue
            mc = run_monte_carlo(daily, initial_equity=100_000.0,
                                 block_size=20, n_sims=2000, seed=42)
            s_ = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
            def _pick(key, default=float("nan")):
                v = s_.get(key, default) if isinstance(s_, dict) else default
                return float(np.median(v)) if isinstance(v, np.ndarray) else v
            mdd = s_.get("max_drawdown_pct") if isinstance(s_, dict) else None
            res["monte_carlo"][name] = {
                "median_maxdd_pct": float(np.median(mdd)) if mdd is not None else None,
                "p5_maxdd_pct": float(np.percentile(mdd, 5)) if mdd is not None else None,
                "P_maxdd_ueber_6pct": float((np.abs(mdd) > 6).mean()) if mdd is not None else None,
                "median_total_return_pct": _pick("total_return_pct"),
                "median_sharpe": _pick("sharpe"),
            }
            m = res["monte_carlo"][name]
            print()
            print(f"  Monte Carlo ({name}, {risk_pct:.2%}/Trade, 2000 Pfade, Block 20):")
            print(f"    Median MaxDD {m['median_maxdd_pct']:.2f}% | P5 {m['p5_maxdd_pct']:.2f}% | "
                  f"P(MaxDD>6%) {m['P_maxdd_ueber_6pct']:.1%} | Median Return {m['median_total_return_pct']:.1f}% | "
                  f"Median Sharpe {m['median_sharpe']:.2f}")

        result["beine"][leg] = res

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
