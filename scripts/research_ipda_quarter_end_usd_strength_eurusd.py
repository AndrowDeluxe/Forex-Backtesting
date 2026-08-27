"""Phase-3-Plausibilitaetscheck fuer IPDA-Kandidat C: Monats-/Quartalsende
USD-Staerke ("Window Dressing", Basel-III-Bilanzoptimierung, Repo-Markt-
Verknappung -- "Das Uhrwerk des Geldes"-PDF, Abschnitte "Window Dressing" /
"Das Quartalsende-Ritual"). Anlass (2026-08-25): User zeigte einen
TradingView-Chart mit einem "IPDA"-Indikator, der Boxen RUECKWIRKEND
zwischen erkannten Pivots zieht (User-Bestaetigung: "Rueckwaerts: Box
zwischen zwei erkannten Pivots gezogen") -- das macht "Zyklus endet in
Hoch/Tief" tautologisch (siehe knowledge/projects/ipda-zyklus-eurusd.md),
liefert also KEINE neue Evidenz fuer die Tag-8/14-Kernthese. User bemerkte
aber zusaetzlich, dass 2025 "sehr sauber ueber die einzelnen Quartale"
gelaufen sei -- das ist eine eigenstaendige, nicht-zirkulaere These
(Quartalsende-Effekt), aber eine Beobachtung an nur 4 Quartalen ist ein
Cherry-Picking-Risiko. Dieses Script testet die These deshalb ueber die
VOLLE Historie, mit 2025 als Einzelfall-Sanity-Check innerhalb des
Gesamtbilds, nicht als Beleg fuer sich.

These (dokumentwoertlich): "Monats- und Quartalsende (Tage 20-22 / 90 Tage):
Zeit fuer die grossen Anpassungen, Basel-III-Reports" + "Repo-Markt wird
trockengelegt" -> USD-Nachfrage steigt -> EUR/USD faellt in den letzten
3-5 Handelstagen vor Monats-/Quartalsende.

Methodik: kumulative Rendite ueber die letzten K Handelstage vor jedem
Monats-/Quartalsende (K in {3,4,5}), Permutationstest (zirkulaerer Shift der
Event-Tage, n=2000, gleiche "rotation"-Methodik wie im Zyklus-Script und in
asian_range_breakout/randomization.py) gegen die Nullhypothese "Rendite in
einem zufaelligen K-Tage-Fenster ist genauso gross". Chronologischer
IS/OOS-Split wie im Zyklus-Script (aeltere 70% / juengere 30%)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from combined_strategy.data import fetch_timeframe

PAIR = "EURUSD"
START, END = "2003-01-01", "2026-08-24"
IS_FRACTION = 0.70

WINDOW_LENGTHS = [3, 4, 5]
N_PERM = 2000
RANDOM_SEED = 42


def period_end_positions(index: pd.DatetimeIndex, quarter_only: bool) -> np.ndarray:
    """Letzter Handelstag jedes Kalendermonats (quarter_only=False) bzw. nur
    Maerz/Juni/September/Dezember (quarter_only=True), als Integer-Position."""
    s = pd.Series(np.arange(len(index)), index=index)
    lasts = s.groupby([index.year, index.month]).tail(1)
    if quarter_only:
        lasts = lasts[lasts.index.month.isin([3, 6, 9, 12])]
    return np.sort(lasts.to_numpy())


def window_returns(close: np.ndarray, end_positions: np.ndarray, k: int) -> np.ndarray:
    """log-Rendite von (end_pos - k) bis end_pos, fuer jede Event-Position mit
    genug Historie davor."""
    valid = end_positions[end_positions - k >= 0]
    return np.log(close[valid] / close[valid - k])


def permutation_pvalue(close: np.ndarray, end_positions: np.ndarray, k: int, rng: np.random.Generator, n_perm: int) -> tuple[float, float, float]:
    """Liefert (beobachtete Durchschnittsrendite, p-Wert zweiseitig,
    p-Wert einseitig fuer die Dokument-Richtung EUR/USD faellt=USD staerker)."""
    n_days = len(close)
    observed = window_returns(close, end_positions, k).mean()

    null_means = np.empty(n_perm)
    for p in range(n_perm):
        shift = int(rng.integers(1, n_days - 1))
        shifted = np.sort((end_positions + shift) % n_days)
        null_means[p] = window_returns(close, shifted, k).mean()

    p_two_sided = np.mean(np.abs(null_means) >= abs(observed))
    p_one_sided_bearish = np.mean(null_means <= observed)  # H1: EUR/USD faellt (Dokument-Richtung)
    return observed, p_two_sided, p_one_sided_bearish


def main():
    print(f"Lade {PAIR} Daily ({START} - {END}) via Dukascopy (gecacht)...")
    df = fetch_timeframe(PAIR, "D1", START, END)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    close_all = df["Close"].to_numpy()

    split_i = int(len(df) * IS_FRACTION)
    is_df, oos_df = df.iloc[:split_i], df.iloc[split_i:]
    print(f"Geladen: {len(df)} Tage, {df.index[0].date()} - {df.index[-1].date()}")
    print(f"IS: {is_df.index[0].date()} - {is_df.index[-1].date()} ({len(is_df)} Tage)")
    print(f"OOS: {oos_df.index[0].date()} - {oos_df.index[-1].date()} ({len(oos_df)} Tage)\n")

    rng = np.random.default_rng(RANDOM_SEED)

    for label, quarter_only in [("Monatsende (alle 12)", False), ("Quartalsende (Mrz/Jun/Sep/Dez)", True)]:
        print(f"=== {label} -- IS-Screening ({is_df.index[0].date()} - {is_df.index[-1].date()}) ===")
        is_close = is_df["Close"].to_numpy()
        ends = period_end_positions(is_df.index, quarter_only)
        n_events = len(ends)
        for k in WINDOW_LENGTHS:
            obs, p2, p1 = permutation_pvalue(is_close, ends, k, rng, N_PERM)
            print(f"  K={k} Tage, n={n_events} Events: mean logret={obs*10000:+.1f} Pips-Aequiv.*, "
                  f"p(2-seitig)={p2:.4f}, p(1-seitig, EUR/USD faellt)={p1:.4f}")
        print()

    # OOS-Bestaetigung nur fuer die dokumentnahe Konfiguration (Quartalsende, K=5,
    # die vom Dokument explizit genannte "letzten 3-5 Handelstage" -- kein
    # Retuning auf OOS, nur EINE Konfiguration einmal gegengeprueft).
    print(f"=== Quartalsende K=5 -- OOS-Bestaetigung ({oos_df.index[0].date()} - {oos_df.index[-1].date()}) ===")
    oos_close = oos_df["Close"].to_numpy()
    oos_ends = period_end_positions(oos_df.index, quarter_only=True)
    obs, p2, p1 = permutation_pvalue(oos_close, oos_ends, 5, rng, N_PERM)
    print(f"  n={len(oos_ends)} Events: mean logret={obs*10000:+.1f} Pips-Aequiv.*, "
          f"p(2-seitig)={p2:.4f}, p(1-seitig, EUR/USD faellt)={p1:.4f}\n")

    # 2025-Einzelfall-Check (User-Beobachtung "2025 lief sehr sauber ueber die
    # Quartale") -- explizit NUR zur Einordnung, nicht als eigenstaendiger Beleg.
    print("=== 2025-Einzelfall (User-Beobachtung, K=5 Handelstage vor Quartalsende) ===")
    df_2025 = df[df.index.year.isin([2024, 2025])]
    ends_2025 = period_end_positions(df.index, quarter_only=True)
    ends_2025 = ends_2025[(df.index[ends_2025].year == 2025)]
    for pos in ends_2025:
        ret = np.log(close_all[pos] / close_all[pos - 5]) * 10000
        print(f"  {df.index[pos].date()}: {ret:+.1f} Pips-Aequiv.* ueber die letzten 5 Handelstage")


if __name__ == "__main__":
    main()
