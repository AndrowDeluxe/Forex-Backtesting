"""OU-Modell: Phase 6 (Robustheit) fuer die empfohlene Konfiguration (2026-09-22).

Nutzerauftrag: "lasse deine Empfehlung noch ueber die anderen Tests der Phase 6
laufen". Geprueft wird die Empfehlung aus der Vertiefung vom 19.09.:

    stop_sigma 8,0 · be_trigger_r 0 (aus) · kein TP · Ausstieg am MA20 ·
    max_hold 10 · Einstieg wie heute live (Folgetags-Eroeffnung, Gate 3,5 %)

Phase-6-Checkliste (app_pages/education_gold_intraday.py). Was die Laeufe vom
16.-19.09. bereits abdecken:
  p6_1 OOS-Split          erledigt (IS 2018-22 / OOS 2023-26, Rangfolge nur IS)
  p6_5 Kosten gemessen    erledigt (research_ou_broker_costs.py, je Broker)
  p6_6 Ausfuehrungs-Lag   erledigt (Einstieg Folgetag statt Signalschluss)
  p6_7 Sizing-Nenner      teilweise (Stopdistanz-Verteilung close_d1) -> hier neu
                          fuer die 8-Sigma-Konfiguration
Was hier nachgeholt wird:
  p6_2 Monte-Carlo-Bootstrap der TRADE-SEQUENZ (Block-Bootstrap wie
       ou_paper_backtest/monte_carlo.py, aber auf Trades statt Tagesrenditen)
  p6_3 Kosten-Sensitivitaet: Spread und Swap bis zum Breakeven sweepen
  p6_4 Jahresaufriss der EMPFOHLENEN Konfiguration (nicht nur der alten)
  p6_7 Hebel-/Stopdistanz-Verteilung bei 8 Sigma
  p6_8 Stop-Abstand gegen Round-Trip-Kosten (Anteil SL < 3x Kosten und deren Ø R)

Aufruf: python research_ou_phase6.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import research_ou_execution_costs as rx  # noqa: E402
import research_ou_execution_optimization as op  # noqa: E402
import research_ou_exit_logic as ex  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = REPO / "ou_paper_backtest" / "results" / "phase6_ou_final_20260922.json"
RISK_PCT = 0.01          # wie live: 1 % Kontorisiko je Trade
SIGMA = 8.0
rng = np.random.default_rng(20260922)


def build(sigma=SIGMA, entry_mode="open_d1"):
    ou_config, ou_portfolio, uni = rx.load_universe()
    ohlc = rx.download([t for v in uni.values() for t in v])
    ma = {t: d["Close"].rolling(ou_config.BB_LOOKBACK).mean() for t, d in ohlc.items()}
    std = {t: d["Close"].rolling(ou_config.BB_LOOKBACK).std() for t, d in ohlc.items()}
    trades = op.model_trades_params(ou_config, ou_portfolio, uni, ohlc, 10, sigma, 0.0)
    out = {}
    for bname in ("FK (TTP)", "EK (Tickmill)"):
        fam = "funded" if bname.startswith("FK") else "ek"
        rows = []
        for tr in trades:
            r = ex.replay_exit(tr, ohlc[tr["ticker"]], ma[tr["ticker"]], std[tr["ticker"]],
                               logic="mean_revert", family=fam, cost=ex.COSTS[bname],
                               be_r=0.0, entry_mode=entry_mode)
            if r:
                rows.append({**r, "ticker": tr["ticker"], "c0": tr["c0"], "stop_dist": tr["stop_dist"]})
        d = pd.DataFrame(rows).sort_values("d0").reset_index(drop=True)
        d["year"] = pd.to_datetime(d["d0"]).dt.year
        out[bname] = d
    return out, trades


# ---------------------------------------------------------------- p6_2
def block_bootstrap_trades(r: np.ndarray, block: int = 10, n_sims: int = 5000) -> dict:
    """Circular Block-Bootstrap auf der TRADE-Sequenz (Muster monte_carlo.py, dort
    auf Tagesrenditen). Bloecke statt Einzeltrades, damit Gute- und
    Schlechtphasen zusammenhaengend bleiben -- genau die Sequenzabhaengigkeit,
    die ein Funded-Konto mit Drawdown-Deckel umbringt.

    Jede Pfad-Equity: equity *= (1 + RISK_PCT * R) je Trade, wie live gesized."""
    n = len(r)
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_sims, n_blocks))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]) % n
    paths = r[idx.reshape(n_sims, -1)][:, :n]

    equity = np.cumprod(1.0 + RISK_PCT * paths, axis=1)
    peak = np.maximum.accumulate(equity, axis=1)
    dd = (equity / peak - 1.0).min(axis=1)
    total = equity[:, -1] - 1.0
    return {
        "n_trades": int(n), "n_sims": n_sims, "block": block,
        "endergebnis_median_pct": round(float(np.median(total)) * 100, 2),
        "endergebnis_p05_pct": round(float(np.quantile(total, 0.05)) * 100, 2),
        "endergebnis_p95_pct": round(float(np.quantile(total, 0.95)) * 100, 2),
        "anteil_pfade_negativ": round(float((total < 0).mean()), 3),
        "maxdd_median_pct": round(float(np.median(dd)) * 100, 2),
        "maxdd_p95_pct": round(float(np.quantile(dd, 0.05)) * 100, 2),   # schlechtestes Ende
        "maxdd_worst_pct": round(float(dd.min()) * 100, 2),
        "P_dd_ueber_4pct": round(float((dd < -0.04).mean()), 3),
        "P_dd_ueber_7pct": round(float((dd < -0.07).mean()), 3),
        "P_dd_ueber_10pct": round(float((dd < -0.10).mean()), 3),
    }


# ---------------------------------------------------------------- p6_3
def cost_sweep(trades, ohlc, ma, std, fam, entry_grid, swap_grid) -> list:
    res = []
    for e in entry_grid:
        for s in swap_grid:
            cost = {"entry_bps": e, "exit_bps": 5.0, "swap_bps_day": s}
            rs = [r["R"] for r in (ex.replay_exit(tr, ohlc[tr["ticker"]], ma[tr["ticker"]], std[tr["ticker"]],
                                                  logic="mean_revert", family=fam, cost=cost, be_r=0.0)
                                   for tr in trades) if r]
            d0 = None
            res.append({"entry_bps": e, "swap_bps_day": s, "avg_R": round(float(np.mean(rs)), 4)})
    return res


def main():
    per_broker, trades = build()
    ou_config, ou_portfolio, uni = rx.load_universe()
    ohlc = rx.download([t for v in uni.values() for t in v])
    ma = {t: d["Close"].rolling(ou_config.BB_LOOKBACK).mean() for t, d in ohlc.items()}
    std = {t: d["Close"].rolling(ou_config.BB_LOOKBACK).std() for t, d in ohlc.items()}
    out = {"konfiguration": f"stop_sigma {SIGMA}, BE aus, kein TP, MA-Ausstieg, max_hold 10, "
                            f"Einstieg Folgetags-Eroeffnung, Risiko {RISK_PCT:.0%}/Trade"}

    for bname, d in per_broker.items():
        oos = d[pd.to_datetime(d["d0"]) >= ex.IS_END]
        print(f"\n=== {bname} === (gesamt {len(d)} Trades, OOS {len(oos)})", flush=True)

        # p6_2 Monte Carlo auf der OOS-Sequenz
        mc = block_bootstrap_trades(oos["R"].to_numpy())
        out[f"{bname} | p6_2_monte_carlo_OOS"] = mc
        print(f"  p6_2 Monte Carlo (OOS, {mc['n_sims']} Pfade, Bloecke von {mc['block']}):", flush=True)
        print(f"       Ergebnis Median {mc['endergebnis_median_pct']:+.2f} % "
              f"(P05 {mc['endergebnis_p05_pct']:+.2f} / P95 {mc['endergebnis_p95_pct']:+.2f}), "
              f"{mc['anteil_pfade_negativ']:.0%} der Pfade negativ", flush=True)
        print(f"       MaxDD Median {mc['maxdd_median_pct']:.2f} %, schlechteste 5 % "
              f"{mc['maxdd_p95_pct']:.2f} %, worst {mc['maxdd_worst_pct']:.2f} %", flush=True)
        print(f"       P(DD > 4 %) {mc['P_dd_ueber_4pct']:.1%} · P(DD > 7 %) {mc['P_dd_ueber_7pct']:.1%} "
              f"· P(DD > 10 %) {mc['P_dd_ueber_10pct']:.1%}", flush=True)

        # p6_4 Jahresaufriss
        jahr = d.groupby("year")["R"].agg(["size", "mean", "sum"]).round(4)
        out[f"{bname} | p6_4_jahre"] = {int(k): {"n": int(v["size"]), "avg_R": float(v["mean"]),
                                                 "sum_R": float(v["sum"])} for k, v in jahr.iterrows()}
        print("  p6_4 Jahre:", " · ".join(f"{int(k)} {v['mean']:+.3f}({int(v['size'])})"
                                          for k, v in jahr.iterrows()), flush=True)

        # p6_7 Hebel / Stopdistanz
        dist = (d["stop_dist"] / d["c0"])
        lev = RISK_PCT / dist
        out[f"{bname} | p6_7_hebel"] = {
            "stopdistanz_median_pct": round(float(dist.median()) * 100, 2),
            "stopdistanz_p05_pct": round(float(dist.quantile(0.05)) * 100, 2),
            "nominal_median_x_konto": round(float(lev.median()), 2),
            "nominal_p95_x_konto": round(float(lev.quantile(0.95)), 2),
            "anteil_stop_unter_5pct": round(float((dist < 0.05).mean()), 3)}
        print(f"  p6_7 Stopdistanz Median {dist.median()*100:.1f} % (P05 {dist.quantile(.05)*100:.1f} %), "
              f"Nominal Median {lev.median():.2f}x Konto, P95 {lev.quantile(.95):.2f}x", flush=True)

        # p6_8 Stop gegen Round-Trip-Kosten
        c = ex.COSTS[bname]
        rt_bps = c["entry_bps"] + c["exit_bps"] + c["swap_bps_day"] * d["cal"]
        ratio = dist * 1e4 / rt_bps
        eng = d[ratio < 3]
        out[f"{bname} | p6_8_stop_vs_kosten"] = {
            "roundtrip_bps_median": round(float(rt_bps.median()), 1),
            "stop_in_vielfachen_der_kosten_median": round(float(ratio.median()), 1),
            "anteil_unter_3x": round(float((ratio < 3).mean()), 4),
            "avgR_unter_3x": round(float(eng["R"].mean()), 4) if len(eng) else None,
            "n_unter_3x": int(len(eng))}
        print(f"  p6_8 Round-Trip {rt_bps.median():.1f} bps, Stop = {ratio.median():.0f}x Kosten, "
              f"Anteil < 3x: {(ratio < 3).mean():.2%} (n={len(eng)})", flush=True)

    # p6_3 Kosten-Sensitivitaet bis zum Breakeven (nur FK -- der teurere Broker)
    print("\n=== p6_3 Kosten-Sensitivitaet (FK-Familie, ganzer Zeitraum) ===", flush=True)
    sweep = cost_sweep(trades, ohlc, ma, std, "funded",
                       entry_grid=[0, 8.45, 16.9, 25, 34, 50, 70], swap_grid=[1.71])
    out["p6_3_spread_sweep"] = sweep
    for r in sweep:
        print(f"  Einstieg {r['entry_bps']:5.1f} bps (Swap {r['swap_bps_day']}): Ø R {r['avg_R']:+.4f}", flush=True)
    sweep2 = cost_sweep(trades, ohlc, ma, std, "funded",
                        entry_grid=[16.9], swap_grid=[0, 1.71, 2.5, 3.5, 5.0, 7.0])
    out["p6_3_swap_sweep"] = sweep2
    for r in sweep2:
        print(f"  Swap {r['swap_bps_day']:4.2f} bps/Tag (Einstieg {r['entry_bps']}): Ø R {r['avg_R']:+.4f}", flush=True)

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print("\ngeschrieben:", OUT)


if __name__ == "__main__":
    main()
