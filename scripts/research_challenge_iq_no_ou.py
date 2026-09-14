"""IQ-Markets-Konto ohne OU-Bein: wie viel Risiko vertragen die verbleibenden
fuenf Beine? (2026-09-13)

Anlass: Der Broker des IQ-Challenge-Kontos (BeyondIQCapital) bietet KEINE
Einzelaktien an -- das OU-Modell-Bein handelt aber genau die (SP500-/
Nasdaq100-Ticker). Der Live-Beleg steht im Bridge-State: in
Funded-Portfolio-Bridge/bridge_state_iqmarkets.json stehen ALLE bisherigen
ou_modell-Signale auf "missed" (nie ein Ticket), waehrend dieselben Signale auf
beiden TTP-Konten als "placed" real gehandelt wurden.

Das Konto faehrt damit faktisch seit Go-Live nur 5 von 6 Beinen -- aber mit dem
Kapitalanteil von 6 (CAPITAL_WEIGHT = 1/6), ein Sechstel des Risikobudgets liegt
also dauerhaft brach. Dieses Skript beziffert, was ein hoeherer Kapitalanteil je
Bein bringt und kostet, und liefert damit die Entscheidungsgrundlage fuer
Funded-Portfolio-Bridge/config.py::AccountConfig.capital_weight.

Methodik komplett aus research_challenge_portfolio_6leg.py importiert
(load_leg/historical_metrics/classify_paths, Block-Bootstrap block_size=20,
n_sims=3000) -- keine zweite Implementierung. Zwei bewusste Abweichungen:

  1. combine_weighted() statt dessen combine_rebalanced(): dort ist das Gewicht
     fest 1/n_legs, hier ist der Kapitalanteil GENAU die freie Variable. Sonst
     identisch (taeglich rebalancierte gewichtete Returns ueber das gemeinsame
     Fenster, ffill ueber Kalendertage).
  2. cls_practical wird aus legs/cls_practical_r100.csv geladen statt _r150:
     das Bein laeuft seit 2026-09-10 mit LEG_RISK_PCT 0.010 statt 0.015 (siehe
     knowledge/projects/cls-practical-kostenvalidierung.md). Mit der r150-Kurve
     waere das Ergebnis systematisch zu optimistisch fuer den heutigen Stand.

Ergebnis (Nutzerentscheid 2026-09-13): capital_weight = 1/3 fuer das
IQ-Konto. Die TTP-Konten bleiben unveraendert bei 6 Beinen @ 1/6, dort sind die
OU-Aktien handelbar."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import research_challenge_portfolio_6leg as base  # noqa: E402

# Siehe Docstring, Abweichung 2 -- muss VOR dem ersten load_leg() gesetzt sein.
base.LEG_FILES["cls_practical"] = "cls_practical_r100"

LEGS_IQ = ("gold_asb", "cls_practical", "trend_pullback", "ctnl_edge", "orb_portfolio")
LEGS_FULL = ("gold_asb", "cls_practical", "ou_modell", "trend_pullback", "ctnl_edge", "orb_portfolio")

# Kapitalanteile, die zur Entscheidung vorgelegt wurden. 1/6 ist der Ist-Zustand
# (Gewicht des vollen 6-Bein-Blends, obwohl nur 5 Beine feuern), 1/3 die
# gewaehlte Stufe.
WEIGHTS = (1 / 6, 1 / 5, 1 / 4.5, 1 / 4, 1 / 3.5, 1 / 3)
CHOSEN_WEIGHT = 1 / 3


def combine_weighted(leg_keys: tuple[str, ...], capital_weight: float) -> pd.Series:
    """Wie base.combine_rebalanced(), nur mit explizitem Kapitalanteil je Bein
    statt fest 1/n_legs (siehe Docstring). Der Rest des Kapitals bleibt
    ungenutzt/unverzinst -- dieselbe Konvention, die die Bridge live faehrt:
    risk_dollars = capital_weight x LEG_RISK_PCT x Equity."""
    sers = {k: base.load_leg(k) for k in leg_keys}
    common_start = max(s.index.min() for s in sers.values())
    common_end = min(s.index.max() for s in sers.values())
    idx = pd.date_range(common_start, common_end, freq="D")
    rets = pd.DataFrame({k: sers[k].reindex(idx).ffill().pct_change() for k in leg_keys}).dropna()
    port_daily = rets.values @ np.full(len(leg_keys), capital_weight)
    return pd.Series(base.INITIAL_EQUITY * (1 + port_daily).cumprod(), index=rets.index)


def evaluate(leg_keys: tuple[str, ...], capital_weight: float) -> dict:
    equity = combine_weighted(leg_keys, capital_weight)
    daily_ret = equity.pct_change().dropna()
    return {
        "legs": list(leg_keys),
        "capital_weight": capital_weight,
        "common_window": {"start": str(equity.index.min().date()), "end": str(equity.index.max().date())},
        "historical_metrics": base.historical_metrics(equity),
        "monte_carlo": {rk: base.classify_paths(daily_ret, rules) for rk, rules in base.RULES.items()},
    }


def _line(label: str, r: dict) -> str:
    h, mc = r["historical_metrics"], r["monte_carlo"]["iqmarkets"]
    return (f"  {label:34s} CAGR {h['cagr_pct']:5.2f}%  MaxDD {h['max_dd_pct']:6.2f}%  "
            f"Sharpe {h['sharpe']:4.2f}  Calmar {h['calmar']:4.2f}  |  IQ: p_breach {mc['p_breach']:.4f}  "
            f"p_target {mc['p_target']:.3f}  Ziel in {mc['median_days_to_target']:.0f} Tagen")


def main():
    print("Referenz: voller 6-Bein-Blend @ 1/6 (das, was auf TTP laeuft und auf IQ\n"
          "gedacht war -- auf IQ feuert das OU-Bein aber nie):")
    reference = evaluate(LEGS_FULL, 1 / 6)
    print(_line("6 Beine @ 1/6", reference))

    print("\nIQ-Konto ohne OU-Bein, nach Kapitalanteil je Bein:")
    by_weight = {}
    for w in WEIGHTS:
        r = evaluate(LEGS_IQ, w)
        by_weight[f"1/{1 / w:.4g}"] = r
        note = ""
        if abs(w - 1 / 6) < 1e-12:
            note = "  <- Ist-Zustand"
        elif abs(w - CHOSEN_WEIGHT) < 1e-12:
            note = "  <- GEWAEHLT (Nutzerentscheid 2026-09-13)"
        print(_line(f"5 Beine @ 1/{1 / w:.4g}", r) + note)

    out = {
        "context": "IQ Markets/BeyondIQCapital handelt keine Einzelaktien -- ou_modell dort ausgeschlossen, "
                   "Kapitalanteil der verbleibenden 5 Beine neu gesetzt. TTP-Konten unveraendert.",
        "cls_leg_file": base.LEG_FILES["cls_practical"],
        "chosen_capital_weight": CHOSEN_WEIGHT,
        "reference_6leg_at_1_6": reference,
        "iq_5leg_by_capital_weight": by_weight,
    }
    out_path = base.RESULTS_DIR / "challenge_portfolio_iq_no_ou.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
