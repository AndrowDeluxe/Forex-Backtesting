"""EUR/USD-only Sweeps (User-Anfrage 2026-08-18), erst hier validieren,
BEVOR auf alle G8-Majors ausgerollt wird:

A) Cross-Filter: welches Zeitfenster fuer den Trend der Referenzpaare
   ("Crosses in der Asia" vs. "Crosses von 6:00-9:00" vs. "seit
   Tagesbeginn") x welche Bestaetigungsschwelle (40% / 50% / 60%).
B) Halte-Test-Zeitpunkt/-Fenster: 09:00 / 09:15 (Baseline) / 09:30 als
   Einzelpunkt, sowie Ranges 09:00-09:30 / 09:00-10:00 / 09:30-10:00
   (muss durchgehend halten, nicht nur an einem Punkt) - GEGEN die
   bestehende, validierte Baseline (kein Cross-Override), um NUR den
   Timing-Effekt zu isolieren, nicht mit dem noch unbewiesenen neuen
   Cross-Filter zu konfundieren.

Methodik wie ueberall in diesem Projekt: Auswahl nur auf In-Sample
(2018-12 bis 2022-06), Validierung der Gewinner auf dem echten Holdout
(2022-06 bis 2026-08), nicht andersrum."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from combined_strategy.data import fetch_timeframe
from cls_practical.currency_strength import compute_cross_vote_confirmation
from cls_practical.data import fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"

EURUSD_BASKET = ["EURGBP", "EURCHF", "EURCAD", "EURAUD", "EURJPY",
                 "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]


def fetch_m5_berlin(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "M5", START, END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def fetch_m15_berlin(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "M15", START, END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def is_oos_stats(trades: pd.DataFrame) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "avg_r": float("nan"), "n_is": 0, "avg_r_is": float("nan"), "n_oos": 0, "avg_r_oos": float("nan")}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    return {
        "n": n, "avg_r": r.mean(), "total_pnl": trades["pnl_usd"].sum(),
        "n_is": int(is_mask.sum()), "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }


def main():
    print("Lade Daten (EUR/USD M5 + 10er-Referenzkorb M15 + 5 Majors fuer die Engine intern + Rates)...")
    eurusd_m5 = fetch_m5_berlin("EURUSD")
    ref_m15 = {p: fetch_m15_berlin(p) for p in EURUSD_BASKET}
    other_majors_m15 = {p: ref_m15[p] for p in cls_advanced.PAIRS if p != "EURUSD" and p in ref_m15}
    for p in cls_advanced.PAIRS:
        if p != "EURUSD" and p not in other_majors_m15:
            other_majors_m15[p] = fetch_m15_berlin(p)
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5)
    direction = daily["direction"]

    # ================================================================
    # A) Cross-Filter: Fenster x Schwelle, IS-Auswahl
    # ================================================================
    print("\n" + "=" * 78 + "\nA) CROSS-FILTER: Fenster x Bestaetigungsschwelle (IS-Auswahl, 2018-12/2022-06)\n" + "=" * 78)
    rows_a = []
    for window in ["asia", "settle", "day_start"]:
        for threshold in [0.4, 0.5, 0.6]:
            conf = compute_cross_vote_confirmation(
                "EURUSD", direction, ref_m15, window=window, confirm_threshold=threshold,
            )
            trades = simulate_cls_practical(
                eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
                cross_confirm_override=conf["confirmed"],
            )
            st = is_oos_stats(trades)
            label = f"window={window:9s} threshold={threshold:.0%}"
            print(f"  {label}: n={st['n']:>3d} avg_R={st['avg_r']:+.3f} | "
                  f"IS(n={st['n_is']:>3d}) avg_R={st['avg_r_is']:+.3f} | "
                  f"OOS(n={st['n_oos']:>3d}) avg_R={st['avg_r_oos']:+.3f}")
            rows_a.append({"window": window, "threshold": threshold, **st})

    df_a = pd.DataFrame(rows_a)
    winner_a = df_a.loc[df_a["avg_r_is"].idxmax()]
    print(f"\n  IS-Gewinner: window={winner_a['window']}, threshold={winner_a['threshold']:.0%} "
          f"(IS avg_R={winner_a['avg_r_is']:+.3f}) -> OOS avg_R={winner_a['avg_r_oos']:+.3f} (n_oos={winner_a['n_oos']:.0f})")

    # ================================================================
    # B) Halte-Test-Zeitpunkt/-Fenster, IS-Auswahl, GEGEN validierte
    #    Baseline (kein Cross-Override) um den Timing-Effekt zu isolieren.
    # ================================================================
    print("\n" + "=" * 78 + "\nB) HALTE-TEST TIMING (IS-Auswahl, kein Cross-Override -- validierte Baseline)\n" + "=" * 78)
    configs_b = [
        ("point_09:00", 9.0, None),
        ("point_09:15 (Baseline)", 9.25, None),
        ("point_09:30", 9.5, None),
        ("range_09:00-09:30", 9.0, 9.5),
        ("range_09:00-10:00", 9.0, 10.0),
        ("range_09:30-10:00", 9.5, 10.0),
    ]
    rows_b = []
    for label, test_hour, test_window_end in configs_b:
        trades = simulate_cls_practical(
            eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
            test_hour=test_hour, test_window_end=test_window_end,
        )
        st = is_oos_stats(trades)
        print(f"  {label:24s}: n={st['n']:>3d} avg_R={st['avg_r']:+.3f} | "
              f"IS(n={st['n_is']:>3d}) avg_R={st['avg_r_is']:+.3f} | "
              f"OOS(n={st['n_oos']:>3d}) avg_R={st['avg_r_oos']:+.3f}")
        rows_b.append({"label": label, "test_hour": test_hour, "test_window_end": test_window_end, **st})

    df_b = pd.DataFrame(rows_b)
    winner_b = df_b.loc[df_b["avg_r_is"].idxmax()]
    print(f"\n  IS-Gewinner: {winner_b['label']} (IS avg_R={winner_b['avg_r_is']:+.3f}) -> "
          f"OOS avg_R={winner_b['avg_r_oos']:+.3f} (n_oos={winner_b['n_oos']:.0f})")

    out_dir = Path(__file__).resolve().parents[1] / "cls_practical" / "results"
    df_a.to_csv(out_dir / "eurusd_cross_filter_window_threshold_sweep.csv", index=False)
    df_b.to_csv(out_dir / "eurusd_holdtest_timing_sweep.csv", index=False)
    print(f"\nGespeichert unter {out_dir}")


if __name__ == "__main__":
    main()
