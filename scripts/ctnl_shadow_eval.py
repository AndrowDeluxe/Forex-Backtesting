"""E6 "mitlaufen lassen": was HAETTEN Long-only und der Regime-Filter gebracht?

Nutzerentscheid 2026-09-23 (E6, Variante d): nichts scharf schalten, sondern
beobachten. Dieses Skript wertet die REAL gehandelten `ctnl_reversal`-Trades
der Bridges aus und stellt sie drei Was-waere-wenn-Varianten gegenueber.

WARUM KEIN EINGRIFF IN DIE BRIDGES NOETIG IST
Beide Merkmale stehen im Nachhinein exakt fest:
  * die RICHTUNG steht im Bridge-State jedes Trades,
  * die REGIME-KENNZAHL ist eine reine Funktion der Kursreihe (Efficiency
    Ratio ueber 100 M15-Bars) und laesst sich zum Signalzeitpunkt
    deterministisch nachrechnen.
Es gibt also nichts, was live mitgeschrieben werden muesste -- eine Aenderung
an einer Bridge waere reines Risiko ohne Informationsgewinn.

DIE SCHWELLE IST EINGEFROREN, NICHT MITLAUFEND
REGIME_THRESHOLD unten ist ein ABSOLUTER Wert (das 50 %-Quantil ueber
2016-2026). Ein mitlaufendes Quantil waere bequemer, macht die Auswertung
aber unreproduzierbar: derselbe Trade koennte beim naechsten Lauf auf der
anderen Seite der Schwelle landen, ohne dass sich etwas geaendert haette
(Fund gold_asb, siehe Memory `gold_asb_liquidity_filter_reproducibility`).
Wird die Schwelle je neu gezogen, gehoert der alte Wert hierher als
Kommentar, damit frueherere Auswertungen nachvollziehbar bleiben.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))

from research_ctnl_execution_costs import _utc_naive  # noqa: E402
from research_ctnl_optimization import regime_feature  # noqa: E402

# Eingefroren 2026-09-23 aus _data/ctnl_direction_regime.json (q50, 2016-2026).
REGIME_THRESHOLD = 0.082677

BRIDGE_STATES = {
    "Funded/ttp": r"C:\Users\andre\Funded-Portfolio-Bridge\bridge_state_ttp.json",
    "Funded/iqmarkets": r"C:\Users\andre\Funded-Portfolio-Bridge\bridge_state_iqmarkets.json",
    "FK": r"C:\Users\andre\FKInstantFunding-MT5-Bridge\bridge_state.json",
}


def load_real_trades() -> pd.DataFrame:
    """Real platzierte ctnl_reversal-Trades aus den Bridge-States."""
    rows = []
    for name, path in BRIDGE_STATES.items():
        try:
            st = json.load(open(path, encoding="utf-8"))
        except FileNotFoundError:
            print(f"  {name}: State nicht gefunden, uebersprungen")
            continue
        for key, v in st.get("positions", {}).items():
            if not isinstance(v, dict) or not str(v.get("leg", "")).startswith("ctnl_reversal"):
                continue
            if not v.get("ticket"):
                continue  # nur real platzierte, keine "missed"
            try:
                sig = pd.Timestamp(key.split("_")[-2])
            except Exception:
                continue
            rows.append({"bridge": name, "signal_zeit": sig,
                         "richtung": int(v.get("direction", 0)),
                         "status": v.get("status"), "ticket": v.get("ticket")})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_shadow_eval.json")
    args = ap.parse_args()

    print("Lese real platzierte ctnl_reversal-Trades aus den Bridge-States ...")
    df = load_real_trades()
    if df.empty:
        print("Keine realen Trades gefunden.")
        return
    print(f"  {len(df)} Trades, "
          f"{df['signal_zeit'].min():%Y-%m-%d} .. {df['signal_zeit'].max():%Y-%m-%d}")

    from gold_smc_htf_ltf.data import fetch_gold_m15
    lo = (df["signal_zeit"].min() - pd.Timedelta(days=40)).strftime("%Y-%m-%d")
    hi = (df["signal_zeit"].max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    bars = fetch_gold_m15(lo, hi, force_refresh=False)
    feat = regime_feature(bars)
    df["regime"] = feat.reindex(_utc_naive(df["signal_zeit"])).to_numpy()

    df["waere_long_only"] = df["richtung"] == 1
    df["waere_regime_ok"] = df["regime"] <= REGIME_THRESHOLD
    df["waere_beides"] = df["waere_long_only"] & df["waere_regime_ok"]

    n = len(df)
    print(f"\n  Eingefrorene Regime-Schwelle: {REGIME_THRESHOLD:.6f}")
    print(f"  {'Variante':>26} {'Trades':>7} {'Anteil':>8}")
    print(f"  {'real gehandelt':>26} {n:>7} {'100.0%':>8}")
    for label, col in (("waere long-only geblieben", "waere_long_only"),
                       ("haette Regime-Filter bestanden", "waere_regime_ok"),
                       ("haette BEIDES bestanden", "waere_beides")):
        k = int(df[col].sum())
        print(f"  {label:>26} {k:>7} {k/n:>7.1%}")

    ohne = df[~df["waere_beides"]]
    print(f"\n  {len(ohne)} Trades waeren NICHT gehandelt worden. Aufschluesselung:")
    print(f"    nur wegen Richtung (short):        {int((~df['waere_long_only'] & df['waere_regime_ok']).sum())}")
    print(f"    nur wegen Regime (Trend zu stark): {int((df['waere_long_only'] & ~df['waere_regime_ok']).sum())}")
    print(f"    wegen beidem:                      {int((~df['waere_long_only'] & ~df['waere_regime_ok']).sum())}")

    print("\n  HINWEIS: P&L je Trade steht in den Bridge-States nicht vollstaendig")
    print("  (verwaiste Eintraege ohne Exit, siehe CHANGELOG 2026-09-19). Diese")
    print("  Auswertung zeigt deshalb die AUSWAHL, nicht das Ergebnis. Sobald genug")
    print("  abgeschlossene Trades vorliegen, gehoert hier ein P&L-Vergleich dazu.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "stand": pd.Timestamp.now(tz="UTC").isoformat(),
        "regime_threshold": REGIME_THRESHOLD,
        "trades_real": n,
        "waere_long_only": int(df["waere_long_only"].sum()),
        "waere_regime_ok": int(df["waere_regime_ok"].sum()),
        "waere_beides": int(df["waere_beides"].sum()),
        "trades": df.to_dict(orient="records"),
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
