"""Zwei Robustheits-Checks fuer den auffaelligsten Fund aus
scripts/research_cls_practical_daily_rate_filter.py (lag=2d, z>=0.5,
filter_mode="and": IS avg_R=+0.916/OOS avg_R=+0.914, aber nur n=62 Trades
total ueber 18 getestete Varianten - Multiple-Comparisons-Risiko), User-
Anfrage 2026-08-19 ("Teste beide Wege"):

A) EUR/USD, derselbe Gewinner-Config: Jahres-Aufschluesselung (Konzentriert
   sich der Effekt auf 1-2 gluckliche Jahre?) + mehrere IS/OOS-Split-Punkte
   statt nur dem einen 2022-06-01-Split (haelt der "schlaegt Baseline auf
   BEIDEN Seiten"-Befund auch bei anderen Split-Punkten?).

B) Dieselbe Filter-Logik auf GBP/USD (UKGILT vs. USTBOND CFD - die einzige
   andere Instrumenten-Kombination, fuer die Dukascopy ueberhaupt einen
   passenden Staatsanleihe-CFD anbietet; USD/JPY, USD/CHF, AUD/USD, USD/CAD
   MUESSEN entfallen, da fuer JPY/CHF/CAD/AUD keine Staatsanleihe-CFD auf
   Dukascopy existiert - verifiziert 2026-08-19, nur BUND/UKGILT/USTBOND
   sind ueberhaupt verfuegbar). GBP/USD hat dieselbe Quote-Waehrungs-
   Konvention wie EUR/USD (USD ist Quote in beiden), compute_daily_rate_score
   kann daher unveraendert wiederverwendet werden (UKGILT statt BUND) - keine
   Vorzeichen-Anpassung noetig, anders als bei USD-als-Basis-Paaren."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from cls_practical.rates import compute_daily_rate_score
from combined_strategy.data import INSTRUMENTS, OFFER_SIDE

import dukascopy_python

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS_EU = [p for p in cls_advanced.PAIRS if p != "EURUSD"]


def fetch_m5_berlin_generic(key: str, start: str, end: str) -> pd.DataFrame:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = dukascopy_python.fetch(
        INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def stats(trades: pd.DataFrame, split: str | None = None) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "avg_r": float("nan"), "n_is": 0, "avg_r_is": float("nan"), "n_oos": 0, "avg_r_oos": float("nan")}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    row = {"n": n, "avg_r": r.mean(), "total_pnl": trades["pnl_usd"].sum()}
    if split is not None:
        is_mask = trades["entry_time"].dt.tz_localize(None) < split
        is_r, oos_r = r[is_mask], r[~is_mask]
        row.update({
            "n_is": int(is_mask.sum()), "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
            "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
        })
    return row


def part_a():
    print("=" * 100 + "\nA) EUR/USD -- Jahres-Aufschluesselung + mehrere Split-Punkte\n" + "=" * 100)
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS_EU}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    baseline = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, use_rates_filter=False)
    score = compute_daily_rate_score(bund_m5, ustbond_m5, lag_days=2)
    filtered = simulate_cls_practical(
        eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
        use_rates_filter=True, rates_score_override=score, rates_z_threshold=0.5, filter_mode="and",
    )

    print(f"\nBaseline n={len(baseline)}, Filter (lag=2d z>=0.5 AND) n={len(filtered)}\n")

    print("-- Jahres-Aufschluesselung (avg_R pro Kalenderjahr) --")
    for label, trades in (("Baseline", baseline), ("Filter", filtered)):
        t = trades.copy()
        t["r"] = t["pnl_usd"] / t["risk_amount_usd"]
        t["year"] = t["entry_time"].dt.year
        yearly = t.groupby("year").agg(n=("r", "size"), avg_r=("r", "mean"))
        print(f"\n  {label}:")
        for year, row in yearly.iterrows():
            print(f"    {year}: n={row['n']:>3.0f} avg_R={row['avg_r']:+.3f}")

    print("\n-- Verschiedene IS/OOS-Split-Punkte (n_is/avg_R_is -> n_oos/avg_R_oos) --")
    splits = ["2020-06-01", "2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01"]
    rows = []
    for split in splits:
        sb = stats(baseline, split)
        sf = stats(filtered, split)
        both_beat = sf["avg_r_is"] > sb["avg_r_is"] and sf["avg_r_oos"] > sb["avg_r_oos"]
        print(f"  Split={split}: Baseline IS(n={sb['n_is']:>3d})={sb['avg_r_is']:+.3f} -> OOS(n={sb['n_oos']:>3d})={sb['avg_r_oos']:+.3f} "
              f"| Filter IS(n={sf['n_is']:>3d})={sf['avg_r_is']:+.3f} -> OOS(n={sf['n_oos']:>3d})={sf['avg_r_oos']:+.3f} "
              f"| beide besser: {both_beat}")
        rows.append({"split": split, "baseline_is": sb["avg_r_is"], "baseline_oos": sb["avg_r_oos"],
                      "filter_is": sf["avg_r_is"], "filter_oos": sf["avg_r_oos"], "both_beat": both_beat})

    out_dir = Path(__file__).resolve().parents[1] / "cls_practical" / "results"
    pd.DataFrame(rows).to_csv(out_dir / "eurusd_daily_rate_filter_split_robustness.csv", index=False)


def part_b():
    print("\n\n" + "=" * 100 + "\nB) GBP/USD (UKGILT vs. USTBOND) -- dieselbe Filter-Logik\n" + "=" * 100)
    print("USD/JPY, USD/CHF, AUD/USD, USD/CAD entfallen: keine Staatsanleihe-CFD fuer "
          "JPY/CHF/CAD/AUD auf Dukascopy verfuegbar (nur BUND/UKGILT/USTBOND existieren).\n")

    gbpusd_m5 = fetch_m5_berlin_generic("GBPUSD", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in cls_advanced.PAIRS if p != "GBPUSD"}
    ukgilt_m5 = fetch_rate_instrument_m5_berlin("UKGILT", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    # GBP/USD hat dieselbe Quote-Waehrungs-Konvention wie EUR/USD (USD = Quote in
    # beiden) -- _USD_IS_QUOTE-Monkeypatch trotzdem noetig fuer die interne
    # Cross-Confirmation (siehe research_cls_practical_multi_instrument.py).
    cls_advanced._USD_IS_QUOTE["EURUSD"] = cls_advanced._USD_IS_QUOTE["GBPUSD"]
    try:
        baseline = simulate_cls_practical(gbpusd_m5, other_majors_m15, ukgilt_m5, ustbond_m5, use_rates_filter=False)

        rows = []
        sb = stats(baseline, "2022-06-01")
        print(f"  Baseline (kein Zinsfilter)             : n={sb['n']:>3d} avg_R={sb['avg_r']:+.3f} | "
              f"IS(n={sb['n_is']:>3d})={sb['avg_r_is']:+.3f} | OOS(n={sb['n_oos']:>3d})={sb['avg_r_oos']:+.3f}")
        rows.append({"label": "baseline", **sb})

        for lag_days in (1, 2, 3):
            score = compute_daily_rate_score(ukgilt_m5, ustbond_m5, lag_days=lag_days)
            for z_threshold in (0.0, 0.25, 0.5):
                for filter_mode in ("and", "majority"):
                    label = f"lag={lag_days}d z>={z_threshold} mode={filter_mode}"
                    trades = simulate_cls_practical(
                        gbpusd_m5, other_majors_m15, ukgilt_m5, ustbond_m5,
                        use_rates_filter=True, rates_score_override=score,
                        rates_z_threshold=z_threshold, filter_mode=filter_mode,
                    )
                    s = stats(trades, "2022-06-01")
                    print(f"  {label:38s}: n={s['n']:>3d} avg_R={s['avg_r']:+.3f} | "
                          f"IS(n={s['n_is']:>3d})={s['avg_r_is']:+.3f} | OOS(n={s['n_oos']:>3d})={s['avg_r_oos']:+.3f}")
                    rows.append({"label": label, "lag_days": lag_days, "z_threshold": z_threshold,
                                 "filter_mode": filter_mode, **s})
    finally:
        cls_advanced._USD_IS_QUOTE["EURUSD"] = True

    df = pd.DataFrame(rows)
    both_beat = df[(df["label"] != "baseline") & (df["avg_r_is"] > sb["avg_r_is"]) & (df["avg_r_oos"] > sb["avg_r_oos"])]
    print(f"\n  Varianten, die die GBP/USD-Baseline auf IS UND OOS gleichzeitig schlagen ({len(both_beat)}):")
    if len(both_beat) == 0:
        print("    keine")
    else:
        for _, r in both_beat.iterrows():
            print(f"    {r['label']}: IS={r['avg_r_is']:+.3f} -> OOS={r['avg_r_oos']:+.3f}")

    out_dir = Path(__file__).resolve().parents[1] / "cls_practical" / "results"
    df.to_csv(out_dir / "gbpusd_daily_rate_filter_sweep.csv", index=False)


if __name__ == "__main__":
    part_a()
    part_b()
