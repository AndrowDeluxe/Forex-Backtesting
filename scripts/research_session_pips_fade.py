"""Kandidat B aus dem SMH-Call "Session Pips" (knowledge/resources/
smh-session-pips-call.md): Dreht der Markt, wenn die laufende Stunde ihre
uebliche Spanne schon gelaufen ist?

Vorab festgelegt (Nutzerentscheid 2026-10-28, vor dem ersten Blick auf Daten):
  Maerkte   EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, GOLD (Dukascopy M5)
  Stunden   08..17 Uhr Berlin (Stundenbeginn), je Stunde 12 M5-Bars
  Ausloeser die laufende Spanne seit hh:00 erreicht den Median der Spanne
            DERSELBEN Stunde ueber die 20 vorherigen Handelstage (Definition
            des Mentors, keine eigene Schwelle). Erste M5-Bar, deren Schluss
            die Spanne erreicht; nicht die letzte Bar der Stunde.
  Richtung  des gelaufenen Moves = Vorzeichen (Schluss Ausloese-Bar - Stunden-
            Eroeffnung); Fade = Gegenrichtung
  Messung   Einstieg zum Schluss der Ausloese-Bar, Ausstieg zum Schluss der
            Stunde (hh:55-Bar). Fade-Ertrag brutto, netto nach Round-Trip-
            Kosten, und normiert auf die Schwelle T.
  Kosten    EURUSD 2,05 Pips (TTP gemessen), GOLD 2,08 bps (TTP gemessen).
            Die anderen Majors sind NICHT gemessen -- ANNAHME: GBPUSD 2,4,
            USDJPY 2,2, USDCHF 2,5, AUDUSD 2,2, USDCAD 2,6 Pips.
  Stufe 1   eine einzige Konfiguration = 1 gezaehlter Versuch.
  Bestanden (IS), wenn BEIDES gilt:
            (a) Mittel des Netto-Fade-Ertrags in Einheiten von T ueber alle
                Maerkte > 0 mit t >= 2 (Tages-Cluster: erst je Kalendertag
                mitteln, dann t-Test ueber die Tage)
            (b) mindestens 4 von 7 Maerkten netto im Mittel > 0
  Sonst verworfen. Einzelstunden und Maerkte werden nur beschreibend gezeigt.

Overfitting-Sperre: Lock "session_pips_fade", IS 2016-01-01..2022-12-31,
OOS 2023-01-01..2025-10-27, Tresor 2025-10-28..2026-10-27.

Aufruf:
    python scripts/research_session_pips_fade.py --stage is
    python scripts/research_session_pips_fade.py --stage oos     # nur nach bestandenem IS
    python scripts/research_session_pips_fade.py --stage tresor  # nur nach OOS
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from research_lock import Lock

STRATEGY = "session_pips_fade"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2022-12-31", "2025-10-27", "2026-10-27"
DATA_START, DATA_END = "2016-01-01", "2026-10-28"
MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "GOLD"]
HOURS = range(8, 18)
LOOKBACK = 20
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDCHF": 1e-4, "AUDUSD": 1e-4, "USDCAD": 1e-4, "USDJPY": 1e-2}
COST_PIPS = {"EURUSD": 2.05, "GBPUSD": 2.4, "USDJPY": 2.2, "USDCHF": 2.5, "AUDUSD": 2.2, "USDCAD": 2.6}
GOLD_COST_BPS = 2.08
CONFIG = {"markets": MARKETS, "hours": list(HOURS), "lookback": LOOKBACK, "trigger": "median",
          "exit": "hour_end", "cost_pips": COST_PIPS, "gold_cost_bps": GOLD_COST_BPS}


def events(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "M5", DATA_START, DATA_END)
    df.index = df.index.tz_convert("Europe/Berlin")
    df = df[df.index.dayofweek < 5]
    df = df[df.index.hour.isin(list(HOURS))].copy()
    df["date"] = df.index.date
    df["hour"] = df.index.hour
    df["k"] = df.index.minute // 5
    g = df.groupby(["date", "hour"], sort=True)
    df["n"] = g["Close"].transform("size")
    df = df[df["n"] == 12]  # nur volle Stunden
    g = df.groupby(["date", "hour"], sort=True)
    df["run_hi"] = g["High"].cummax()
    df["run_lo"] = g["Low"].cummin()
    df["hour_open"] = g["Open"].transform("first")
    df["hour_close"] = g["Close"].transform("last")

    rng = g.agg(hi=("High", "max"), lo=("Low", "min"))
    rng["range"] = rng["hi"] - rng["lo"]
    piv = rng["range"].unstack("hour")
    thr = piv.rolling(LOOKBACK, min_periods=LOOKBACK).median().shift(1)  # nur Vortage
    thr = thr.stack().rename("T")
    df = df.join(thr, on=["date", "hour"]).dropna(subset=["T"])

    hit = (df["run_hi"] - df["run_lo"] >= df["T"]) & (df["k"] < 11)
    first = df[hit].groupby(["date", "hour"]).head(1).copy()
    direction = np.sign(first["Close"] - first["hour_open"])
    first = first[direction != 0]
    direction = direction[direction != 0]
    fade = -direction * (first["hour_close"] - first["Close"])
    if key == "GOLD":
        cost = first["Close"] * GOLD_COST_BPS / 10_000
        unit = first["Close"] * 1e-4  # 1 bp
    else:
        cost = COST_PIPS[key] * PIP[key]
        unit = PIP[key]
    out = pd.DataFrame({
        "market": key, "date": pd.to_datetime(first["date"]), "hour": first["hour"],
        "trigger_k": first["k"], "T_units": first["T"] / unit,
        "gross_units": fade / unit, "net_units": (fade - cost) / unit,
        "gross_T": fade / first["T"], "net_T": (fade - cost) / first["T"],
    })
    out.attrs["hours_total"] = int(len(rng.dropna()))
    return out.reset_index(drop=True)


def window(d: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    return d[(d["date"] >= pd.Timestamp(start)) & (d["date"] <= pd.Timestamp(end))]


def cluster_t(d: pd.DataFrame, col: str) -> tuple[float, float, int]:
    day = d.groupby("date")[col].mean()
    return day.mean(), day.mean() / (day.std(ddof=1) / np.sqrt(len(day))), len(day)


def report(d: pd.DataFrame, label: str) -> bool:
    unit = "Pips (Gold: bps)"
    print(f"\n{'=' * 110}\n{label}: {len(d):,} Ereignisse\n{'=' * 110}")
    per = d.groupby("market").agg(
        n=("net_T", "size"), T=("T_units", "median"), brutto=("gross_units", "mean"),
        netto=("net_units", "mean"), brutto_T=("gross_T", "mean"), netto_T=("net_T", "mean"),
        treffer=("gross_units", lambda s: 100 * (s > 0).mean()))
    print(f"Je Markt (Mittelwerte; T = Median-Schwelle in {unit}):")
    print(per.to_string(float_format=lambda v: f"{v:,.3f}"))
    m_g, t_g, nd = cluster_t(d, "gross_T")
    m_n, t_n, _ = cluster_t(d, "net_T")
    pos = int((per["netto"] > 0).sum())
    print(f"\nAlle Maerkte (Tages-Cluster, {nd} Tage): brutto {m_g:+.4f} T (t {t_g:+.2f}) | "
          f"netto {m_n:+.4f} T (t {t_n:+.2f}) | Maerkte netto > 0: {pos}/7")
    print("\nJe Stunde (alle Maerkte, Mittel in T):")
    print(d.groupby("hour").agg(n=("net_T", "size"), brutto_T=("gross_T", "mean"),
                                netto_T=("net_T", "mean")).T.to_string(float_format=lambda v: f"{v:+.3f}"))
    passed = (m_n > 0) and (t_n >= 2.0) and (pos >= 4)
    print(f"\nRegel (a) netto > 0 mit t >= 2: {m_n > 0 and t_n >= 2.0} | (b) >= 4/7 Maerkte: {pos >= 4} "
          f"-> {'BESTANDEN' if passed else 'NICHT BESTANDEN'}")
    return passed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("is", "oos", "tresor"), required=True)
    stage = ap.parse_args().stage
    lock = Lock(STRATEGY)
    lock.register_split(IS_START, IS_END, OOS_END, TRESOR_END)

    d = pd.concat([events(k) for k in MARKETS], ignore_index=True)
    if stage == "is":
        if lock.trials == 0:
            lock.log_trials(1, note="Stufe 1: Fade nach Median-Ausschoepfung, 7 Maerkte, 08-17 Uhr")
        print(f"Versuche im Register: {lock.trials}")
        ok = report(window(d, IS_START, IS_END), f"IS {IS_START}..{IS_END}")
        lock_note = "naechster Schritt: --stage oos" if ok else "verworfen, OOS bleibt versiegelt"
        print(f"\n{lock_note}")
        return

    h = lock.freeze(CONFIG)
    start, end = lock.unseal(stage, h)
    report(window(d, start, end), f"{stage.upper()} {start}..{end} (einmalig geoeffnet)")


if __name__ == "__main__":
    main()
