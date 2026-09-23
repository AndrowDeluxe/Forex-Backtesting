"""EK-Kalibrierung vom 2026-09-10 komplett nachrechnen (Nutzerauftrag 2026-09-23).

ANLASS: beim Nachholen der ORB-Kalibrierung ergab dieselbe Rechnung fuer EKs
IST-Zustand P(MaxDD>40%) = 33,9 %, waehrend der Kommentar in
EK-Portfolio-Bridge/config.py 7,8 % nennt. Der historische MaxDD stimmte exakt
(-38,1 %), nur die Zukunftsrechnung nicht.

VORGEHEN (in dieser Reihenfolge, damit die Ursache eindeutig wird):
 1. PIPELINE VALIDIEREN: die beiden in ek_v2_realistic_final.json
    gespeicherten Kombinationen auf IHREM Fenster (2018-12-01..2024-12-30)
    nachrechnen. Treffe ich CAGR/MaxDD/Sharpe/Endkapital, rechnet meine
    Pipeline wie die Studie -- erst dann sind Aussagen ueber die Differenz
    belastbar.
 2. FENSTER ISOLIEREN: dieselbe Kombination auf dem Studienfenster vs. bis
    heute (2026). 2025/2026 sind in der Studie nicht enthalten.
 3. HORIZONT ISOLIEREN: die Studie nennt einen MC-Median-DD von -26,1 % bei
    einem historischen MaxDD von -38,1 %. Ein MC ueber DIESELBE Pfadlaenge
    muesste im Median NAHE am historischen Wert liegen, nicht deutlich
    darunter -- das ist der Hinweis auf einen kuerzeren simulierten Horizont
    (z. B. 1 Jahr statt 6 Jahre). Diese Hypothese wird hier direkt geprueft.
 4. ERGEBNIS: sagen, welche Zahl welche Frage beantwortet.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LEGS = ROOT / "portfolio_construction" / "results" / "legs"
STUDY = json.loads((ROOT / "portfolio_construction" / "results" / "ek_v2_realistic_final.json").read_text())

RNG = np.random.default_rng(20260923)
N_PATHS = 3000

LEG_FILE = {"gold_asb": "gold_asb", "trend_pullback": "trend_pullback",
            "btc_ema_cross": "btc_ema_cross", "gold_silver": "gold_silver_divergenz_r100",
            "cls_practical": "cls_practical", "ou_modell": "ou_modell"}

# Ist-Zustand der Bridge (EK-Portfolio-Bridge/config.py), effektiv = 1/8 x LEG_RISK_PCT
DEPLOYED_EFFECTIVE = {"gold_asb": 2.9337, "trend_pullback": 1.8337, "btc_ema_cross": 2.9337,
                      "gold_silver": 2.9337, "cls_practical": 0.5500, "ou_modell": 0.3663}


def leg_1pct() -> dict[str, pd.Series]:
    out = {}
    for leg, f in LEG_FILE.items():
        s = pd.read_csv(LEGS / f"{f}.csv", parse_dates=["date"]).set_index("date")["equity"]
        out[leg] = s.pct_change().dropna()
    return out


def portfolio(base: dict[str, pd.Series], weights: dict[str, float],
              start: str, end: str) -> pd.Series:
    frame = pd.concat(base, axis=1).sort_index().loc[start:end].fillna(0.0)
    return sum(frame[leg] * w for leg, w in weights.items())


def metrics(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    return {"cagr_pct": (eq.iloc[-1] ** (1 / years) - 1) * 100,
            "max_dd_pct": (eq / eq.cummax() - 1).min() * 100,
            "sharpe": r.mean() / r.std() * np.sqrt(252),
            "final_equity": eq.iloc[-1] * 100_000}


def mc(r: pd.Series, horizon_days: int | None = None, block: str = "month") -> dict:
    """horizon_days=None -> Pfade so lang wie die Historie."""
    if block == "month":
        blocks = [g.to_numpy() for _, g in r.groupby([r.index.year, r.index.month])]
        avg = np.mean([len(b) for b in blocks])
        n_blocks = len(blocks) if horizon_days is None else max(1, int(round(horizon_days / avg)))
        idx = RNG.integers(0, len(blocks), size=(N_PATHS, n_blocks))
        paths = (np.concatenate([blocks[j] for j in idx[i]]) for i in range(N_PATHS))
    else:  # iid-Tage
        arr = r.to_numpy()
        n = len(arr) if horizon_days is None else horizon_days
        paths = (RNG.choice(arr, size=n, replace=True) for _ in range(N_PATHS))
    worst = np.empty(N_PATHS)
    for i, p in enumerate(paths):
        eq = np.cumprod(1 + p)
        worst[i] = (eq / np.maximum.accumulate(eq) - 1).min()
    return {"median_dd_pct": float(np.median(worst) * 100),
            "p_gt_20": float((worst < -0.20).mean()),
            "p_gt_40": float((worst < -0.40).mean())}


def main() -> int:
    base = leg_1pct()
    w_start, w_end = STUDY["common_window"]["start"], STUDY["common_window"]["end"]

    print("=" * 100)
    print("SCHRITT 1 -- Pipeline gegen die gespeicherten Studienzahlen validieren")
    print(f"Fenster der Studie: {w_start} .. {w_end}")
    for name in ("reference", "riskopt_20dd"):
        combo = {k: float(v.strip("%")) for k, v in STUDY[name]["combo"].items()}
        r = portfolio(base, combo, w_start, w_end)
        got, want = metrics(r), STUDY[name]["historical_metrics"]
        print(f"\n{name}  (Gewichte: " + ", ".join(f"{k} {v}%" for k, v in combo.items()) + ")")
        print(f"{'':22s} {'Studie':>12} {'nachgerechnet':>14} {'Abweichung':>12}")
        for key, label in (("cagr_pct", "CAGR %"), ("max_dd_pct", "MaxDD %"),
                           ("sharpe", "Sharpe"), ("final_equity", "Endkapital")):
            d = got[key] - want[key]
            print(f"  {label:20s} {want[key]:>12,.2f} {got[key]:>14,.2f} {d:>+12,.2f}")

    print("\n" + "=" * 100)
    print("SCHRITT 2 -- Ist-Zustand der Bridge: Studienfenster vs. bis heute")
    print(f"{'Fenster':<28} {'CAGR %':>9} {'MaxDD %':>9} {'Sharpe':>7} {'Tage':>6}")
    for label, (s0, s1) in (("Studie (bis 2024-12-30)", (w_start, w_end)),
                            ("bis heute (2026)", (w_start, "2026-12-31"))):
        r = portfolio(base, DEPLOYED_EFFECTIVE, s0, s1)
        m = metrics(r)
        print(f"{label:<28} {m['cagr_pct']:>9.1f} {m['max_dd_pct']:>9.1f} {m['sharpe']:>7.2f} {len(r):>6}")

    print("\n" + "=" * 100)
    print("SCHRITT 3 -- Woher kommen die 7,8 %? Horizont und Methode isolieren")
    print("Studie nennt fuer den Ist-Zustand: MC-Median-DD -26,1 %, P(MaxDD>40%) 7,8 %")
    r_deployed = portfolio(base, DEPLOYED_EFFECTIVE, w_start, w_end)
    print(f"(historischer MaxDD auf dem Studienfenster: {metrics(r_deployed)['max_dd_pct']:.1f} %)")
    print(f"\n{'Simulierter Horizont':<26} {'Methode':<14} {'Median-DD %':>12} {'P(DD>40%)':>11}")
    for horizon, hlabel in ((252, "1 Jahr"), (504, "2 Jahre"), (756, "3 Jahre"), (None, "volle Historie")):
        for block in ("month", "iid"):
            res = mc(r_deployed, horizon, block)
            mark = ""
            if abs(res["median_dd_pct"] - (-26.1)) < 2.0 and abs(res["p_gt_40"] - 0.078) < 0.03:
                mark = "   <== trifft die Studienzahlen"
            print(f"{hlabel:<26} {('Monatsbloecke' if block=='month' else 'iid-Tage'):<14} "
                  f"{res['median_dd_pct']:>12.1f} {res['p_gt_40']:>10.1%}{mark}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
