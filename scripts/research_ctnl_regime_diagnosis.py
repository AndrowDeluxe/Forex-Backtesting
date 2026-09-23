"""CTNL Edge: woran scheitert das Vorregime? (Diagnose, 2026-09-23)

Anlass: die Kostenvalidierung (research_ctnl_execution_costs.py,
knowledge/projects/ctnl-kostenvalidierung.md) ergab bei GEMESSENEN Kosten
2023-2026 fuer beide Beine PF > 1,2. Dieselbe Rechnung auf 2016-01..2024-08:

    ctnl_continuation   430 Trades   Ø R -0,206 .. -0,248   PF 0,74-0,88
    ctnl_reversal     1.115 Trades   Ø R -0,085 .. +0,076   PF 0,91-1,08

Die Kostenkorrektur rettet das Vorregime also NICHT -- sie deckt sich mit dem
Phase-6-Walk-Forward (negativ in allen 4 Sub-Perioden, siehe
knowledge/projects/gold-ctnl-edge-portfolio.md). Die Strategie funktioniert
nur im Regime ab ca. 2024-08, auf dem sie auch entwickelt und "FINAL locked"
wurde.

DIESES SKRIPT OPTIMIERT NICHTS. Es ist rein deskriptiv und beantwortet die
Vorfrage: WORAN scheitert das Vorregime? Davon haengt ab, ob eine
Parametersuche ueberhaupt der richtige Hebel ist -- und welcher. Ohne diese
Antwort waere jede Suche auf 25 bereits durchgekaemmten Sweep-Skripten eine
weitere Runde Regime-Anpassung.

Fuenf Achsen:
  D1  Ø R / PF / Trefferquote je Kalenderjahr. Gleichmaessig schlecht oder
      an wenigen Jahren haengend? Das sind zwei voellig verschiedene Diagnosen.
  D2  Exit-Reason-Mix je Regime. Sterben die Trades am Stop oder verhungern
      sie an der Haltedauer? Trennt "falscher Einstieg" von "Ziel unerreichbar".
  D3  MFE-Verteilung. Wie weit kamen die Trades ins Plus, bevor sie starben?
      DIREKTE Antwort auf die TP-Frage: liegt die Masse bei 2R, ist ein
      5R-Ziel dort strukturell unerreichbar. Liegt sie bei 0, sind die
      Einstiege falsch und kein Exit-Parameter rettet das.
  D4  MAE-Verteilung der GEWINNER. Wie tief gingen sie ins Minus? DIREKTE
      Antwort auf die SL-Frage: ein engerer Stop ist nur dann gratis, wenn
      kaum ein Gewinner ihn beruehrt haette.
  D5  Gibt es einen beobachtbaren Regime-Zustand, der gute von schlechten
      Phasen VORAB trennt? Vorarbeit fuer einen Regime-Waechter -- und
      zugleich der Test, ob sich so einer ueberhaupt bauen laesst. Findet
      sich nichts, ist das ein ebenso wertvolles Ergebnis.

mfe_r/mae_r liegen bereits im Trade-Output von strategy/backtest.py -- D3/D4
brauchen also keine neue Simulation, nur eine Auswertung.
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

from research_ctnl_execution_costs import (  # noqa: E402  -- bewusst wiederverwendet
    _assert_live_config_match,
    _utc_naive,
    build_trades,
    load_bars,
    replay_with_lag,
)

# Grenze zwischen Vor- und Gutregime. NICHT gefittet, sondern uebernommen aus
# der Phase-6-Walk-Forward-Aufteilung (gold-ctnl-edge-portfolio.md: "Das
# 2024-08/2026-08-Fenster ist der einzige durchweg positive Zeitraum").
REGIME_SPLIT = pd.Timestamp("2024-08-01")

BAR_MINUTES = {"ctnl_continuation": 5, "ctnl_reversal": 15}
REAL_LAG = 1  # der reale Betriebspunkt, siehe ctnl-kostenvalidierung.md Befund 1


def _stats(r: pd.Series) -> dict:
    r = r.dropna()
    if r.empty:
        return {"trades": 0}
    wins, losses = r[r > 0], r[r <= 0]
    return {
        "trades": int(len(r)),
        "avg_r": float(r.mean()),
        "median_r": float(r.median()),
        "summe_r": float(r.sum()),
        "trefferquote": float((r > 0).mean()),
        "profit_factor": (float(wins.sum() / abs(losses.sum()))
                          if len(losses) and losses.sum() != 0 else float("nan")),
    }


# ------------------------------------------------------------------ D1


def d1_per_year(rep: pd.DataFrame, leg: str) -> dict:
    """Ø R / PF / Trefferquote je Kalenderjahr."""
    df = rep[rep["effective_risk"] > 0].copy()
    df["jahr"] = _utc_naive(df["entry_time"]).dt.year
    print(f"\n  D1 -- {leg}: je Kalenderjahr (Lag {REAL_LAG}, mit R-Detektor)")
    print(f"    {'Jahr':>6} {'Trades':>7} {'ØR':>8} {'MedR':>8} {'PF':>6} {'Treffer':>8} {'ΣR':>9}")
    out = {}
    for jahr, sub in df.groupby("jahr"):
        s = _stats(sub["r"])
        out[int(jahr)] = s
        print(f"    {jahr:>6} {s['trades']:>7} {s['avg_r']:>+8.3f} {s['median_r']:>+8.3f} "
              f"{s['profit_factor']:>6.2f} {s['trefferquote']:>7.1%} {s['summe_r']:>+9.1f}")
    pos = sum(1 for s in out.values() if s.get("avg_r", 0) > 0)
    print(f"    -> {pos} von {len(out)} Jahren positiv")
    return out


# ------------------------------------------------------------------ D2


def d2_exit_mix(trades: pd.DataFrame, leg: str) -> dict:
    """Exit-Reason-Mix je Regime, mit Ø R je Grund."""
    df = trades.copy()
    df["regime"] = np.where(_utc_naive(df["entry_time"]) < REGIME_SPLIT, "vor", "gut")
    print(f"\n  D2 -- {leg}: Exit-Gruende je Regime")
    out = {}
    for regime in ("vor", "gut"):
        sub = df[df["regime"] == regime]
        if sub.empty:
            continue
        print(f"    {regime}regime ({len(sub)} Trades):")
        reasons = {}
        for grund, g in sub.groupby("exit_reason"):
            anteil = len(g) / len(sub)
            avg = float(g["r_multiple"].mean())
            reasons[str(grund)] = {"n": int(len(g)), "anteil": float(anteil), "avg_r": avg}
            print(f"      {str(grund):<12} {len(g):>5} ({anteil:>5.1%})  Ø R {avg:>+7.3f}")
        out[regime] = reasons
    return out


# ------------------------------------------------------------------ D3


def d3_mfe(trades: pd.DataFrame, leg: str) -> dict:
    """Wie weit kamen die Trades ins Plus? Direkte TP-Diagnose."""
    df = trades.copy()
    df["regime"] = np.where(_utc_naive(df["entry_time"]) < REGIME_SPLIT, "vor", "gut")
    print(f"\n  D3 -- {leg}: MFE-Verteilung (wie weit ins Plus, in R)")
    print(f"    {'Regime':>8} {'n':>6} {'p50':>7} {'p75':>7} {'p90':>7} {'p95':>7} {'max':>8}")
    out = {}
    for regime in ("vor", "gut"):
        sub = df[df["regime"] == regime]
        if sub.empty:
            continue
        m = sub["mfe_r"].dropna()
        q = {f"p{p}": float(m.quantile(p / 100)) for p in (50, 75, 90, 95)}
        out[regime] = {"n": int(len(m)), **q, "max": float(m.max())}
        print(f"    {regime:>8} {len(m):>6} {q['p50']:>7.2f} {q['p75']:>7.2f} "
              f"{q['p90']:>7.2f} {q['p95']:>7.2f} {m.max():>8.2f}")

    # Der entscheidende Schnitt: welcher Anteil haette welches R-Ziel erreicht?
    print(f"    Anteil der Trades, die ein Ziel von X R ueberhaupt BERUEHRT haetten:")
    print(f"    {'Regime':>8} " + " ".join(f"{x:>7}" for x in ("1R", "2R", "3R", "4R", "5R", "6R")))
    reach = {}
    for regime in ("vor", "gut"):
        sub = df[df["regime"] == regime]
        if sub.empty:
            continue
        m = sub["mfe_r"].dropna()
        row = {f"{x}R": float((m >= x).mean()) for x in (1, 2, 3, 4, 5, 6)}
        reach[regime] = row
        print(f"    {regime:>8} " + " ".join(f"{row[f'{x}R']:>6.1%}" for x in (1, 2, 3, 4, 5, 6)))
    out["ziel_erreichbarkeit"] = reach
    return out


# ------------------------------------------------------------------ D4


def d4_mae(trades: pd.DataFrame, leg: str) -> dict:
    """Wie tief gingen die GEWINNER ins Minus? Direkte SL-Diagnose."""
    df = trades.copy()
    df["regime"] = np.where(_utc_naive(df["entry_time"]) < REGIME_SPLIT, "vor", "gut")
    print(f"\n  D4 -- {leg}: MAE der GEWINNER (wie tief ins Minus, in R)")
    print(f"    {'Regime':>8} {'Gewinner':>9} {'p50':>7} {'p75':>7} {'p90':>7} {'max':>7}")
    out = {}
    for regime in ("vor", "gut"):
        sub = df[(df["regime"] == regime) & (df["r_multiple"] > 0)]
        if sub.empty:
            continue
        m = sub["mae_r"].dropna().abs()
        q = {f"p{p}": float(m.quantile(p / 100)) for p in (50, 75, 90)}
        out[regime] = {"n": int(len(m)), **q, "max": float(m.max())}
        print(f"    {regime:>8} {len(m):>9} {q['p50']:>7.2f} {q['p75']:>7.2f} "
              f"{q['p90']:>7.2f} {m.max():>7.2f}")
    # Was wuerde ein engerer Stop kosten? Anteil der Gewinner, die ihn
    # beruehrt haetten -- das ist die Obergrenze des Schadens.
    print(f"    Anteil der GEWINNER, die ein auf X R verengter Stop gekillt haette:")
    print(f"    {'Regime':>8} " + " ".join(f"{x:>7}" for x in ("0.3R", "0.5R", "0.7R", "0.9R")))
    kill = {}
    for regime in ("vor", "gut"):
        sub = df[(df["regime"] == regime) & (df["r_multiple"] > 0)]
        if sub.empty:
            continue
        m = sub["mae_r"].dropna().abs()
        row = {f"{x}R": float((m >= x).mean()) for x in (0.3, 0.5, 0.7, 0.9)}
        kill[regime] = row
        print(f"    {regime:>8} " + " ".join(f"{row[f'{x}R']:>6.1%}" for x in (0.3, 0.5, 0.7, 0.9)))
    out["gewinner_gekillt"] = kill
    return out


# ------------------------------------------------------------------ D5


def d5_regime_state(rep: pd.DataFrame, bars: pd.DataFrame, leg: str) -> dict:
    """Gibt es einen VORAB beobachtbaren Zustand, der gute von schlechten
    Phasen trennt?

    Bewusst nur Kennzahlen, die zum Einstiegszeitpunkt ohne Blick nach vorn
    verfuegbar sind. Getestet wird nicht "korreliert irgendwas", sondern:
    teilt man die Trades nach dem Quartil der Kennzahl, unterscheiden sich
    die R-Ergebnisse dann? Nur das waere als Filter verwertbar.
    """
    idx = _utc_naive(bars.index)
    close = bars["close"]
    px = pd.Series(close.to_numpy(), index=idx)

    # ATR-Proxy in % des Preises, 100 Bars rueckwaerts
    tr = (bars["high"] - bars["low"]).to_numpy()
    atr_pct = pd.Series(tr, index=idx).rolling(100).mean() / px * 100
    # Trendstaerke: |Preisaenderung| / Summe der Absolutbewegungen (Efficiency Ratio)
    chg = px.diff(100).abs()
    path = px.diff().abs().rolling(100).sum()
    eff_ratio = chg / path
    # Langfrist-Drift: Preis relativ zum 500-Bar-Mittel
    drift = (px / px.rolling(500).mean() - 1) * 100

    feats = {"ATR_pct": atr_pct, "Effizienz": eff_ratio, "Drift_pct": drift}
    df = rep[rep["effective_risk"] > 0].copy()
    df["t"] = _utc_naive(df["entry_time"])

    print(f"\n  D5 -- {leg}: trennt ein vorab beobachtbarer Zustand?")
    out = {}
    for name, ser in feats.items():
        vals = ser.reindex(df["t"]).to_numpy()
        d = df.assign(feat=vals).dropna(subset=["feat"])
        if len(d) < 40:
            print(f"    {name:<10} zu wenige Datenpunkte ({len(d)})")
            continue
        try:
            d["q"] = pd.qcut(d["feat"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
        except ValueError:
            continue
        row = {}
        cells = []
        for q, g in d.groupby("q", observed=True):
            s = _stats(g["r"])
            row[str(q)] = s
            cells.append(f"{str(q)}: ØR {s['avg_r']:+.3f} (n={s['trades']})")
        out[name] = row
        spread = max(v["avg_r"] for v in row.values()) - min(v["avg_r"] for v in row.values())
        print(f"    {name:<10} " + " | ".join(cells))
        print(f"    {'':<10} Spanne zwischen bestem und schlechtestem Quartil: {spread:.3f} R")
    return out


# ----------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    ap.add_argument("--measured-bps", type=float, default=1.95,
                    help="Gemessene Round-Trip-Kosten (Default: TTP, der teuerste "
                         "der vier Broker -- konservativ)")
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_regime_diagnosis.json")
    args = ap.parse_args()

    _assert_live_config_match()

    print(f"Lade Gold-Bars {args.start} .. {args.end} ...")
    bars = load_bars(args.start, args.end)
    for k, v in bars.items():
        print(f"  {k}: {len(v):,} Bars")

    frac = args.measured_bps / 10_000.0
    trades = build_trades(bars, args.measured_bps)
    bar_source = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}

    result = {"start": args.start, "end": args.end, "measured_bps": args.measured_bps,
              "regime_split": str(REGIME_SPLIT.date()),
              "beine": {}}

    for leg, tr in trades.items():
        if tr.empty:
            continue
        print(f"\n{'='*78}\n{leg}: {len(tr)} Trades gesamt\n{'='*78}")
        rep = replay_with_lag(tr, bar_source[leg], REAL_LAG, frac)
        rep = rep[rep["consumed_r"] <= 0.50]  # R-Detektor, wie live

        # Kontrollzahl: stimmt das Gesamtbild mit der Kostenvalidierung ueberein?
        gesamt = _stats(rep["r"])
        print(f"  Kontrolle (Lag {REAL_LAG}, mit Gate): {gesamt['trades']} handelbar, "
              f"Ø R {gesamt['avg_r']:+.3f}, PF {gesamt['profit_factor']:.2f}")

        result["beine"][leg] = {
            "gesamt": gesamt,
            "d1_je_jahr": d1_per_year(rep, leg),
            "d2_exit_mix": d2_exit_mix(tr, leg),
            "d3_mfe": d3_mfe(tr, leg),
            "d4_mae": d4_mae(tr, leg),
            "d5_regime": d5_regime_state(rep, bar_source[leg], leg),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
