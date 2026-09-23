"""EK: Hebel auf EIN-JAHRES-Sicht kalibrieren (Nutzerentscheid 2026-09-23).

VORGABE DES NUTZERS: "Die 40% Grenze sollte ueber ein Jahr halten, im besten
Fall sollte jedes Jahr positiv sein. Meine Risikobereitschaft ist da aber sehr
offen, passe das Risiko an die groessere Option an."

Damit aendert sich die Messgroesse gegenueber dem Audit: nicht mehr der
Drawdown ueber die volle Historie, sondern ueber ein rollierendes Jahr. Zwei
Kennzahlen entscheiden:
  1. P(MaxDD > 40 % innerhalb eines Jahres)  -- die harte Grenze
  2. P(Jahresergebnis < 0)                   -- der Wunsch "jedes Jahr positiv"

ou_modell wird NICHT mitskaliert (Nutzerhinweis 2026-09-23: "OU wird gerade
nochmal umgebaut und dann separat verifiziert"). Es behaelt sein heutiges
Gewicht -- auch deshalb, weil es out-of-sample negativ ist und seine 4,40x
ohnehin offen sind.

NEBENBEDINGUNG, die sonst still zuschlaegt: EKs MAX_SINGLE_TRADE_RISK_PCT
LEHNT einen Trade AB (SizingError), statt ihn zu verkleinern. Bei 3 % und
Beinen auf 2,93 % wuerde schon Hebel 1,02x dazu fuehren, dass gold_asb,
btc_ema_cross und gold_silver gar nicht mehr handeln. Der Deckel muss also mit
dem Hebel mitwachsen -- das Skript rechnet den noetigen Wert mit aus.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LEGS = ROOT / "portfolio_construction" / "results" / "legs"

RNG = np.random.default_rng(20260923)
N_PATHS = 4000
YEAR_DAYS = 252

LEG_FILE = {"gold_asb": "gold_asb", "trend_pullback": "trend_pullback",
            "btc_ema_cross": "btc_ema_cross", "gold_silver": "gold_silver_divergenz_r100",
            "cls_practical": "cls_practical", "ou_modell": "ou_modell"}
# effektives Risiko je Trade heute (= CAPITAL_WEIGHT 1/8 x LEG_RISK_PCT)
TODAY = {"gold_asb": 2.9337, "trend_pullback": 1.8337, "btc_ema_cross": 2.9337,
         "gold_silver": 2.9337, "cls_practical": 0.5500, "ou_modell": 0.3663}
ORB_TODAY = 0.30          # je Instrument, seit 2026-09-22
NO_SCALE = {"ou_modell"}  # wird separat verifiziert


def load():
    base = {}
    for leg, f in LEG_FILE.items():
        s = pd.read_csv(LEGS / f"{f}.csv", parse_dates=["date"]).set_index("date")["equity"]
        base[leg] = s.pct_change().dropna()
    return base


def orb_stream() -> pd.Series:
    """ORB unter Variante C, aus dem Kalibrierungslauf uebernommen."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("c", ROOT / "scripts" / "research_ek_orb_risk_calibration.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.orb_returns_per_1pct()


def year_stats(r: pd.Series) -> dict:
    """Rollierendes Jahr per Block-Bootstrap ueber Kalendermonate (12 Monate)."""
    blocks = [g.to_numpy() for _, g in r.groupby([r.index.year, r.index.month])]
    idx = RNG.integers(0, len(blocks), size=(N_PATHS, 12))
    dd = np.empty(N_PATHS)
    ret = np.empty(N_PATHS)
    for i in range(N_PATHS):
        path = np.concatenate([blocks[j] for j in idx[i]])
        eq = np.cumprod(1 + path)
        dd[i] = (eq / np.maximum.accumulate(eq) - 1).min()
        ret[i] = eq[-1] - 1
    return {"p_dd40": float((dd < -0.40).mean()), "p_dd20": float((dd < -0.20).mean()),
            "median_dd": float(np.median(dd)), "p_neg_year": float((ret < 0).mean()),
            "median_ret": float(np.median(ret)), "q05_ret": float(np.percentile(ret, 5))}


def main() -> int:
    base = load()
    base["orb"] = orb_stream()
    frame = pd.concat(base, axis=1).sort_index()
    start = max(s.dropna().index.min() for s in base.values())
    end = min(s.dropna().index.max() for s in base.values())
    frame = frame.loc[start:end].fillna(0.0)
    print(f"Fenster: {start.date()} .. {end.date()} ({len(frame)} Tage)\n")

    def portfolio(k: float) -> pd.Series:
        r = sum(frame[leg] * (w if leg in NO_SCALE else w * k) for leg, w in TODAY.items())
        return r + frame["orb"] * ORB_TODAY * k

    print("Hebel auf alle Beine AUSSER ou_modell (das bleibt, wird separat verifiziert)")
    print(f"{'Hebel':>6} {'groesstes Bein':>15} {'noetiger Cap':>13} {'Median Jahr':>12} "
          f"{'P(Jahr<0)':>10} {'P(DD>40%)':>10} {'P(DD>20%)':>10} {'5%-Jahr':>9}")
    rows = []
    for k in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.3, 2.6, 3.0):
        r = portfolio(k)
        st = year_stats(r)
        biggest = max(w * k for leg, w in TODAY.items() if leg not in NO_SCALE)
        rows.append({"k": k, "biggest": biggest, **st})
        print(f"{k:>5.1f}x {biggest:>14.2f}% {np.ceil(biggest*1.15)/100:>12.0%} "
              f"{st['median_ret']:>11.0%} {st['p_neg_year']:>9.1%} {st['p_dd40']:>9.1%} "
              f"{st['p_dd20']:>9.1%} {st['q05_ret']:>8.0%}")

    print("\nEntscheidungsregel: groesster Hebel mit P(MaxDD>40% im Jahr) <= 10 %")
    print("(10,3 % war die Toleranz, die die Studie vom 2026-09-10 selbst akzeptiert hat)")
    ok = [r for r in rows if r["p_dd40"] <= 0.10]
    best = max(ok, key=lambda r: r["k"]) if ok else rows[0]
    print(f"-> Hebel {best['k']:.1f}x | Median-Jahr {best['median_ret']:.0%} | "
          f"P(Jahr<0) {best['p_neg_year']:.1%} | P(DD>40%) {best['p_dd40']:.1%}")
    print(f"   groesstes Einzelbein danach: {best['biggest']:.2f} % je Trade "
          f"-> MAX_SINGLE_TRADE_RISK_PCT muss auf mindestens {np.ceil(best['biggest']*1.15)/100:.0%} "
          f"(sonst lehnt core/sizing.py diese Trades AB)")
    print("\nLEG_RISK_PCT neu (= effektiv / CAPITAL_WEIGHT 1/8):")
    for leg, w in TODAY.items():
        neu = w if leg in NO_SCALE else w * best["k"]
        note = "  (unveraendert, wird separat verifiziert)" if leg in NO_SCALE else ""
        print(f"  {leg:16s} {neu/100/0.125:.4f}   -> effektiv {neu:.3f} %{note}")
    print(f"  {'orb_* (je Instr.)':16s} {ORB_TODAY*best['k']/100/0.125:.4f}   "
          f"-> effektiv {ORB_TODAY*best['k']:.3f} %")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
