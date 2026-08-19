"""EUR/USD-only Fein-Sweep des Halte-Test-Zeitpunkts/-Fensters (User-Anfrage
2026-08-19, Folge-Test zu scripts/research_cls_practical_window_threshold_holdtest_sweep.py
Sweep B): "Teste bitte nochmal andere Zeitfenster von 8:30 Uhr - 10:30 Uhr
einzelne Zeiten im 15min Takt sowie Ranges im 30min Takt."

- Punkt-Modus: Einzelzeitpunkte auf dem 15-Minuten-Raster 08:30-10:30
  (9 Werte).
- Range-Modus: alle Fenster [start, end) mit start < end auf dem
  30-Minuten-Raster 08:30-10:30 (5 Rasterpunkte -> 10 Kombinationen), muss
  ueber das GESAMTE Fenster halten (nicht nur an einem Punkt).

GEGEN die bestehende, validierte Baseline (kein Cross-Override), um NUR den
Timing-Effekt zu isolieren - exakt wie im vorigen Sweep B.

Wichtiger Unterschied zum vorigen Lauf: cls_practical/engine.py wurde
2026-08-19 gefixt, damit die Entry-Suche nie VOR der Aufloesung des
Checkpoints selbst beginnt (sonst Lookahead fuer Checkpoints >= 09:30,
z.B. point_09:30 oder alle Ranges, deren Ende > 09:30 liegt) - betrifft
hier also fast alle Konfigurationen jenseits der 09:15/09:00-Baseline.

Methodik wie ueberall in diesem Projekt: Auswahl nur auf In-Sample
(2018-12 bis 2022-06), Validierung der Gewinner auf dem echten Holdout
(2022-06 bis 2026-08), nicht andersrum."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from combined_strategy.data import fetch_timeframe
from cls_practical.data import fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"

BASELINE_LABEL = "point_09:15 (Baseline)"


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


def hhmm(h: float) -> str:
    total_min = round(h * 60)
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


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


def build_configs() -> list[tuple[str, float, float | None]]:
    configs = []
    # Punkt-Modus: 15-Minuten-Raster 08:30-10:30
    point_hours = [8.5 + 0.25 * i for i in range(9)]  # 8.5 .. 10.5
    for h in point_hours:
        label = f"point_{hhmm(h)}"
        if abs(h - 9.25) < 1e-9:
            label += " (Baseline)"
        configs.append((label, h, None))

    # Range-Modus: 30-Minuten-Raster 08:30-10:30, alle start<end Kombinationen
    grid_hours = [8.5 + 0.5 * i for i in range(5)]  # 8.5, 9.0, 9.5, 10.0, 10.5
    for i, start in enumerate(grid_hours):
        for end in grid_hours[i + 1:]:
            configs.append((f"range_{hhmm(start)}-{hhmm(end)}", start, end))

    return configs


def main():
    print("Lade Daten (EUR/USD M5 + 5 Majors M15 fuer die Engine intern + Rates)...")
    eurusd_m5 = fetch_m5_berlin("EURUSD")
    other_majors_m15 = {p: fetch_m15_berlin(p) for p in cls_advanced.PAIRS if p != "EURUSD"}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    configs = build_configs()
    print(f"\n{len(configs)} Konfigurationen ({sum(1 for _, _, e in configs if e is None)} Punkte, "
          f"{sum(1 for _, _, e in configs if e is not None)} Ranges)\n")

    print("=" * 88 + "\nHALTE-TEST TIMING FEINRASTER (IS-Auswahl, kein Cross-Override -- validierte Baseline)\n" + "=" * 88)
    rows = []
    for label, test_hour, test_window_end in configs:
        trades = simulate_cls_practical(
            eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
            test_hour=test_hour, test_window_end=test_window_end,
        )
        st = is_oos_stats(trades)
        print(f"  {label:24s}: n={st['n']:>3d} avg_R={st['avg_r']:+.3f} | "
              f"IS(n={st['n_is']:>3d}) avg_R={st['avg_r_is']:+.3f} | "
              f"OOS(n={st['n_oos']:>3d}) avg_R={st['avg_r_oos']:+.3f}")
        rows.append({"label": label, "test_hour": test_hour, "test_window_end": test_window_end,
                      "mode": "range" if test_window_end is not None else "point", **st})

    df = pd.DataFrame(rows)
    baseline = df.loc[df["label"] == BASELINE_LABEL].iloc[0]

    winner_is = df.loc[df["avg_r_is"].idxmax()]
    print(f"\nIS-Gewinner: {winner_is['label']} (IS avg_R={winner_is['avg_r_is']:+.3f}) -> "
          f"OOS avg_R={winner_is['avg_r_oos']:+.3f} (n_oos={winner_is['n_oos']:.0f})")
    print(f"Baseline ({BASELINE_LABEL}): IS avg_R={baseline['avg_r_is']:+.3f} -> OOS avg_R={baseline['avg_r_oos']:+.3f}")

    both_beat = df[(df["avg_r_is"] > baseline["avg_r_is"]) & (df["avg_r_oos"] > baseline["avg_r_oos"]) & (df["label"] != BASELINE_LABEL)]
    print(f"\nKonfigurationen, die die Baseline auf IS UND OOS GLEICHZEITIG schlagen ({len(both_beat)}):")
    if len(both_beat) == 0:
        print("  keine")
    else:
        for _, r in both_beat.sort_values("avg_r_is", ascending=False).iterrows():
            print(f"  {r['label']:24s}: IS avg_R={r['avg_r_is']:+.3f} (n={r['n_is']:.0f}) -> "
                  f"OOS avg_R={r['avg_r_oos']:+.3f} (n={r['n_oos']:.0f})")

    out_dir = Path(__file__).resolve().parents[1] / "cls_practical" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "eurusd_holdtest_timing_finegrid_sweep.csv", index=False)
    print(f"\nGespeichert unter {out_dir / 'eurusd_holdtest_timing_finegrid_sweep.csv'}")


if __name__ == "__main__":
    main()
