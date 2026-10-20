"""Regimekarte berechnen und fuer den Makro-Agenten ablegen.

    python -m fusion_lab.macro_regime [--refresh]

Ausgabe nach fusion_lab/data/macro_regime/ (gitignored):
  current.json     aktueller Zustand + Kennzahlen des aktuellen Regimes (Agent-Input)
  regime_map.md    lesbare Karte: Stand, naechste Prints, Tabellen je Linse
  labels.parquet   Regime je Handelstag
  stats_<lens>.csv Rendite/Vola/Sharpe je Regime und Asset
  calibration.md   Abgleich mit den Zahlen im Original-PDF (Stand 18.09.2026)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import model as m
from .data import ASSETS, asset_excess_returns, fetch_release_dates

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_regime"

# Referenzwerte aus dem PDF (A. Landi, Stand 18.09.2026, Bloomberg-Daten ab 03/1994)
PDF_ASOF = "2026-09-18"
PDF_DAYS = 8385
PDF_COUNTS = {
    "change": {"g↓ π↓": 2319, "g↑ π↑": 2172, "g↑ π↓": 2057, "g↓ π↑": 1837},
    "signs": {"g↑ π↑": 7883, "g↓ π↑": 247, "g↓ π↓": 208, "g↑ π↓": 113},
    "joint": {"g↑·slow × π↑·slow": 2143, "g↑·accel × π↑·accel": 1977,
              "g↑·accel × π↑·slow": 1976, "g↑·slow × π↑·accel": 1721},
}
PDF_SNAPSHOT = {  # Regime g↑·slow × π↑·accel: (Rendite, Vola, Sharpe)
    "SPX": (4.5, 16.6, 0.27), "UST": (4.2, 4.3, 0.96), "Gold": (3.3, 16.4, 0.20),
    "Copper": (-6.4, 21.4, -0.30), "Crude": (-9.5, 37.3, -0.26),
    "Wheat": (-36.2, 29.0, -1.25), "DXY": (-3.1, 7.3, -0.43),
}

LENS_TITLE = {"joint": "Gemeinsame Sicht (bevorzugt)", "change": "Beschleunigt vs. verlangsamt",
              "signs": "Nur Vorzeichen"}


def current_state(refresh: bool) -> dict:
    """Zustand nach dem letzten Print (gilt ab der naechsten Sitzung)."""
    state = {}
    for kind in ("growth", "inflation"):
        p = m.classify(m.prints(kind, refresh)).iloc[-1]
        state[kind] = {"release": p["release"].date().isoformat(), "period": p["period"].date().isoformat(),
                       "yoy": round(p["yoy"], 2), "yoy_prev_period": round(p["yoy_prev_period"], 2),
                       "up": bool(p["up"]), "accel": bool(p["accel"])}
    g, i = state["growth"], state["inflation"]
    a = lambda b: "↑" if b else "↓"
    s = lambda b: "accel" if b else "slow"
    state["labels"] = {"signs": f"g{a(g['up'])} π{a(i['up'])}",
                       "change": f"g{a(g['accel'])} π{a(i['accel'])}",
                       "joint": f"g{a(g['up'])}·{s(g['accel'])} × π{a(i['up'])}·{s(i['accel'])}"}
    return state


def next_releases(refresh: bool) -> dict:
    today = pd.Timestamp.today().normalize()
    out = {}
    for kind, name in (("growth", "GDP"), ("inflation", "CPI")):
        dates = fetch_release_dates(kind, refresh=refresh)
        out[name] = [d.date().isoformat() for d in dates[dates > today][:2]]
    return out


def regime_since(labels: pd.DataFrame, lens: str = "joint") -> str:
    lab = labels[lens]
    changed = lab.ne(lab.shift())
    return changed[changed].index[-1].date().isoformat()


def fmt_table(stats: pd.DataFrame, field: str, current: str, digits: int) -> str:
    t = stats[field][ASSETS].round(digits)
    head = "| Regime | Tage | " + " | ".join(ASSETS) + " |\n|---|---:|" + "---:|" * len(ASSETS) + "\n"
    rows = []
    for reg, row in t.iterrows():
        mark = "**" if reg == current else ""
        cells = " | ".join("–" if pd.isna(v) else f"{v:.{digits}f}" for v in row)
        rows.append(f"| {mark}{reg}{mark} | {int(stats.loc[reg, ('days', 'n')])} | {cells} |")
    return head + "\n".join(rows)


def calibration(excess: pd.DataFrame, refresh: bool) -> str:
    ex = excess[(excess.index >= m.SAMPLE_START) & (excess.index <= PDF_ASOF)]
    lab = m.daily_labels(ex.index, refresh=refresh)
    lines = [f"# Kalibrierung gegen das Original (Stand {PDF_ASOF})", "",
             f"Handelstage: Nachbau {len(lab)}, PDF {PDF_DAYS}. Regime am Stichtag: "
             f"{lab['joint'].iloc[-1]} (PDF: g↑·slow × π↑·accel).", ""]
    for lens, ref in PDF_COUNTS.items():
        vc = lab[lens].value_counts()
        lines += [f"## Tage je Regime: {lens}", "", "| Regime | Nachbau | Anteil | PDF | Anteil |",
                  "|---|---:|---:|---:|---:|"]
        for reg, n_pdf in ref.items():
            n = int(vc.get(reg, 0))
            lines.append(f"| {reg} | {n} | {n / len(lab):.1%} | {n_pdf} | {n_pdf / PDF_DAYS:.1%} |")
        lines.append("")
    st = m.regime_stats(ex, lab, "joint").loc["g↑·slow × π↑·accel"]
    lines += ["## Asset-Kennzahlen im Regime g↑·slow × π↑·accel", "",
              "| Asset | Rendite | PDF | Vola | PDF | Sharpe | PDF |", "|---|---:|---:|---:|---:|---:|---:|"]
    for a in ASSETS:
        r, v, s = PDF_SNAPSHOT[a]
        lines.append(f"| {a} | {st[('ret', a)]:.1f} | {r} | {st[('vol', a)]:.1f} | {v} | "
                     f"{st[('sharpe', a)]:.2f} | {s} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="FRED/yfinance neu laden")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    excess = asset_excess_returns(args.refresh)
    excess = excess[excess.index >= m.SAMPLE_START]
    labels = m.daily_labels(excess.index, refresh=args.refresh)
    labels.to_parquet(OUT_DIR / "labels.parquet")

    state = current_state(args.refresh)
    state["next_releases"] = next_releases(args.refresh)
    state["regime_since"] = regime_since(labels)
    state["sample"] = {"start": labels.index[0].date().isoformat(),
                       "end": labels.index[-1].date().isoformat(), "days": len(labels)}

    md = ["# Wachstums-Inflations-Regimekarte", "",
          f"Stand Daten: {state['sample']['end']} · Stichprobe {state['sample']['start']} bis "
          f"{state['sample']['end']} ({len(labels)} Handelstage) · Nachbau nach A. Landi (20.09.2026)", ""]
    g, i = state["growth"], state["inflation"]
    md += ["## Wo wir stehen", "", "| | YoY vorher | YoY aktuell | Vorzeichen | Tempo | Print |",
           "|---|---:|---:|---|---|---|",
           f"| Wachstum (reales BIP, {g['period']}) | {g['yoy_prev_period']:.2f} % | {g['yoy']:.2f} % | "
           f"{'positiv' if g['up'] else 'negativ'} | {'beschleunigt' if g['accel'] else 'verlangsamt'} | {g['release']} |",
           f"| Inflation (CPI, {i['period'][:7]}) | {i['yoy_prev_period']:.2f} % | {i['yoy']:.2f} % | "
           f"{'positiv' if i['up'] else 'negativ'} | {'beschleunigt' if i['accel'] else 'verlangsamt'} | {i['release']} |",
           "", f"**Regime:** {state['labels']['joint']} (seit {state['regime_since']}, gilt ab der Sitzung "
           f"nach dem letzten Print).", "",
           "Naechste Prints (FRED-Kalender): " + "; ".join(f"{k} {', '.join(v)}" for k, v in state["next_releases"].items()),
           ""]

    for lens in m.LENSES:
        stats = m.regime_stats(excess, labels, lens)
        stats.to_csv(OUT_DIR / f"stats_{lens}.csv")
        cur = state["labels"][lens]
        if lens == "joint" and cur in stats.index:
            row = stats.loc[cur]
            n = int(row[("days", "n")])
            state["current_regime_stats"] = {
                "days": n, "share": round(n / len(labels), 3),
                **{a: {"ret_pa": round(row[("ret", a)], 2), "vol_pa": round(row[("vol", a)], 2),
                       "sharpe": round(row[("sharpe", a)], 2)} for a in ASSETS}}
        md += [f"## {LENS_TITLE[lens]}", "", "Aktuelles Regime **fett**. Werte vs. Cash, annualisiert.", "",
               "### Rendite % p.a.", "", fmt_table(stats, "ret", cur, 1), "",
               "### Sharpe", "", fmt_table(stats, "sharpe", cur, 2), "",
               "### Vola % p.a.", "", fmt_table(stats, "vol", cur, 1), ""]

    md += ["## Lesehinweise", "",
           "- Seltene Regime (wenige hundert Tage oder weniger) sind Rauschen; nur die vier grossen "
           "Zustaende der gemeinsamen Sicht tragen.",
           "- Rohstoffe ab Aug. 2000 und ohne Rollrendite (yfinance-Front-Monat), UST als synthetische "
           "5y-Anleihe. Details: fusion_lab/macro_regime/data.py.",
           "- Karte der Vergangenheit, keine Prognose. Fuer Handelsregeln gilt die Overfitting-Sperre.", ""]

    (OUT_DIR / "regime_map.md").write_text("\n".join(md), encoding="utf-8")
    (OUT_DIR / "current.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "calibration.md").write_text(calibration(excess, args.refresh), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
