"""OOS-Robustheits-Check fuer den staerksten Fund aus
scripts/research_cls_practical_external_filters.py (User-Anfrage 2026-08-13,
IS-only 2018-12-01..2022-06-01, OOS-Verifikation dort bewusst zurueckgestellt
und bis heute (2026-08-20) nie nachgeholt): "nur mittlere 60% Asia-Range-
Breite" (Q20-Q80 der Range asia_high-asia_low) hob avg_R IS von +0.155 auf
+0.292 bei fast gleichem total_R trotz deutlich weniger Trades (85->47).

Methodik wie research_cls_practical_daily_rate_filter_robustness.py Teil A
(User-Vorgabe 2026-08-19, "Teste beide Wege"): mehrere IS/OOS-Split-Punkte
statt nur dem einen Split + Jahres-Aufschluesselung. WICHTIGER Unterschied
zum Original-Script: die Q20/Q80-Schwellen werden hier PRO SPLIT nur aus dem
jeweiligen IS-Abschnitt bestimmt und dann auf IS+OOS gemeinsam angewendet -
das Original-Script hatte die Schwellen aus dem gesamten (damals IS-only)
Sample gezogen, was bei einer Ausweitung auf den vollen Datumsbereich sonst
ein Lookahead waere (die Breiten-Verteilung der Zukunft waere live nicht
bekannt). Reiner Datums-Ausschluss auf bereits erzeugten Baseline-Trades
(kein Eingriff in engine.py), analog zum Original-Script."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS, compute_daily_features

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
SPLITS = ["2020-06-01", "2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01"]
REFERENCE_SPLIT = "2022-06-01"  # derselbe Split wie im Original-Fund, fuer die Jahres-Aufschluesselung


def stats(trades: pd.DataFrame, split: str) -> dict:
    if len(trades) == 0:
        return {"n": 0, "n_is": 0, "avg_r_is": float("nan"), "total_r_is": 0.0,
                "n_oos": 0, "avg_r_oos": float("nan"), "total_r_oos": 0.0}
    t = trades.copy()
    t["r"] = t["pnl_usd"] / t["risk_amount_usd"]
    is_mask = t["date"].astype(str) < split
    is_r, oos_r = t.loc[is_mask, "r"], t.loc[~is_mask, "r"]
    return {
        "n": len(t),
        "n_is": len(is_r), "avg_r_is": is_r.mean() if len(is_r) else float("nan"), "total_r_is": is_r.sum(),
        "n_oos": len(oos_r), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"), "total_r_oos": oos_r.sum(),
    }


def normal_width_days(range_width: pd.Series, split: str) -> set:
    """Q20/Q80-Schwellen NUR aus dem IS-Teil (< split), angewendet auf den
    gesamten Kalender (IS+OOS) - so waeren die Schwellen an jedem OOS-Tag
    schon vorher bekannt gewesen (rollend waere praeziser, aber ein fixer,
    nur-aus-der-Vergangenheit-gezogener Schwellenwert ist die minimal
    noetige Lookahead-Vermeidung fuer diesen Robustheits-Check)."""
    is_width = range_width[range_width.index.astype(str) < split]
    q20, q80 = is_width.quantile(0.20), is_width.quantile(0.80)
    return set(range_width[(range_width >= q20) & (range_width <= q80)].index)


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    baseline = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    daily = compute_daily_features(eurusd_m5)
    range_width = daily["asia_high"] - daily["asia_low"]
    print(f"Baseline n={len(baseline)} Trades, {len(daily)} Handelstage insgesamt.\n")

    print("=" * 110)
    print("Jahres-Aufschluesselung (avg_R pro Kalenderjahr), Schwelle aus IS < " + REFERENCE_SPLIT)
    print("=" * 110)
    normal_days_ref = normal_width_days(range_width, REFERENCE_SPLIT)
    filtered_ref = baseline[baseline["date"].isin(normal_days_ref)]
    print(f"Gefiltert (mittlere 60% Range-Breite, Schwelle aus IS): n={len(filtered_ref)} von {len(baseline)}\n")

    for label, trades in (("Baseline", baseline), ("Filter (mittlere 60% Breite)", filtered_ref)):
        t = trades.copy()
        t["r"] = t["pnl_usd"] / t["risk_amount_usd"]
        t["year"] = pd.to_datetime(t["date"].astype(str)).dt.year
        yearly = t.groupby("year").agg(n=("r", "size"), avg_r=("r", "mean"))
        print(f"  {label}:")
        for year, row in yearly.iterrows():
            print(f"    {year}: n={row['n']:>3.0f} avg_R={row['avg_r']:+.3f}")
        print()

    print("=" * 110)
    print("Mehrere IS/OOS-Split-Punkte (Schwelle jeweils NEU aus dem eigenen IS-Teil bestimmt)")
    print("=" * 110)
    rows = []
    for split in SPLITS:
        normal_days = normal_width_days(range_width, split)
        filtered = baseline[baseline["date"].isin(normal_days)]
        sb = stats(baseline, split)
        sf = stats(filtered, split)
        both_beat = (sf["avg_r_is"] > sb["avg_r_is"]) and (sf["avg_r_oos"] > sb["avg_r_oos"])
        print(f"  Split={split}: Baseline IS(n={sb['n_is']:>3d})={sb['avg_r_is']:+.3f} -> OOS(n={sb['n_oos']:>3d})={sb['avg_r_oos']:+.3f} "
              f"| Filter IS(n={sf['n_is']:>3d})={sf['avg_r_is']:+.3f} -> OOS(n={sf['n_oos']:>3d})={sf['avg_r_oos']:+.3f} "
              f"| beide besser: {both_beat}")
        rows.append({"split": split, "baseline_n_is": sb["n_is"], "baseline_avg_r_is": sb["avg_r_is"],
                      "baseline_n_oos": sb["n_oos"], "baseline_avg_r_oos": sb["avg_r_oos"],
                      "filter_n_is": sf["n_is"], "filter_avg_r_is": sf["avg_r_is"],
                      "filter_n_oos": sf["n_oos"], "filter_avg_r_oos": sf["avg_r_oos"], "both_beat": both_beat})

    n_both_beat = sum(r["both_beat"] for r in rows)
    print(f"\n  -> schlaegt Baseline auf IS UND OOS gleichzeitig bei {n_both_beat}/{len(rows)} Split-Punkten.")

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "asia_range_width_split_robustness.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
