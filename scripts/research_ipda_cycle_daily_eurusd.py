"""Phase-3-Plausibilitaetscheck (education_gold_intraday.py-Checkliste) fuer
die IPDA-Kernthese aus "Das Uhrwerk des Geldes" (Dennis Schwer Consulting
PDF, vom User am 2026-08-24 geteilt): der Markt bewegt sich angeblich in
~18-22-Handelstage-Zyklen mit Wendepunkten ("Shift Candles") um Tag 8 und
Tag 14 des Zyklus.

Das Dokument selbst laesst den Zyklus-Anker ("0-Punkt") bewusst vage
("vielleicht ist 1.1 ..., vielleicht 1.4 der erste Freitag ..." -- reine
Spekulation, keine feste Regel). User-Vorgabe (2026-08-24, per
AskUserQuestion + Nachtrag): Anker ist im Optimalfall der 1. Handelstag
jedes Kalendermonats, aber realistischerweise +/-10 Handelstage variabel.
Wir raten deshalb NICHT einen festen Anker, sondern scannen alle Offsets in
diesem Fenster (und mehrere Zykluslaengen 18-22) und pruefen per
Permutationstest (zirkulaerer Shift der Pivot-Serie, analog zur
"rotation"-Methode in asian_range_breakout/randomization.py), ob IRGENDEINE
Kombination eine echte, nicht nur zufaellige Haeufung von Trendwechseln um
Tag 8/14 zeigt -- inklusive einer Mehrfachvergleichs-korrigierten
Gesamt-p-Wert ueber das ganze Raster, damit wir uns nicht durch die Auswahl
des besten von ~105 getesteten Kandidaten selbst ein Ergebnis herbeireden.

Das ist Phase 3 ("Plausibilitaet grob abschaetzen, DUENNES/unklares
Material aussortieren, BEVOR Zeit in den Nachbau geht") -- noch kein
fertiger Trading-Edge mit Entry/Exit/Risk, nur die Vorfrage: gibt es das
Zyklus-Muster ueberhaupt in echten EUR/USD-Daily-Daten?

Chronologischer Split: aeltere ~70% der verfuegbaren Historie = In-Sample
zum Screenen (dieses Script), juengere ~30% = Out-of-Sample, hier NUR fuer
die im IS besten Kandidaten einmal gegengeprueft (kein Retuning auf OOS).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from combined_strategy.data import fetch_timeframe
from strategy.indicators import compute_atr

PAIR = "EURUSD"
START, END = "2003-01-01", "2026-08-24"
IS_FRACTION = 0.70  # aeltere 70% zum Screenen, juengere 30% = OOS-Bestaetigung

ATR_PERIOD = 14
ATR_MULT = 1.5  # ZigZag-Schwelle: Umkehr muss >= ATR_MULT * ATR(14) betragen

OFFSET_RANGE = range(-10, 11)  # Monatsanfang +/- 10 Handelstage (User-Vorgabe)
CYCLE_LENGTHS = [18, 19, 20, 21, 22]
TARGET_DAYS_AT_L20 = {"tag8": 8, "tag14": 14}  # auf andere Zykluslaengen skaliert
WINDOW = 1  # Toleranzfenster um den Zieltag (+/- 1 Handelstag)

N_PERM = 2000
RANDOM_SEED = 42


# --------------------------------------------------------------------------
# 1. ZigZag-Pivots (volatilitaetsadaptive Schwelle statt fixer Prozentsatz)
# --------------------------------------------------------------------------
def zigzag_pivots(df: pd.DataFrame, atr_mult: float, atr_period: int) -> pd.DataFrame:
    """Klassischer ZigZag auf Close: ein neuer Pivot (Hoch/Tief) wird erst
    bestaetigt, wenn der Preis seit dem letzten bestaetigten Extrem um
    mindestens `atr_mult * ATR(atr_period)` (zum Pivot-Zeitpunkt) in die
    Gegenrichtung gelaufen ist. Liefert die trading-day-Integer-Position
    (0..n-1) jedes bestaetigten Pivots -- das ist unsere Definition von
    "Trendwechsel/Wendepunkt", die das Dokument nie praezisiert.

    Zwei Phasen: (1) Bootstrap mit getrenntem laufendem Max/Min, bis eine der
    beiden Schwankungen die Schwelle reisst (legt fest, ob der erste
    bestaetigte Pivot ein Hoch oder Tief ist, je nachdem welches Extrem
    zeitlich zuerst kam); (2) danach eindeutige Einzel-Extrem-Verfolgung mit
    strikt alternierender Richtung (Standard-ZigZag-Invariante)."""
    lower = df.rename(columns=str.lower)
    atr = compute_atr(lower, n=atr_period)
    close = df["Close"].to_numpy()
    n = len(close)

    start_pos = df.index.get_loc(atr.first_valid_index())
    pivots: list[tuple[int, str]] = []
    direction = 0  # 0=unbekannt (Bootstrap), 1=verfolge Hoch (letzter Pivot war Tief), -1=verfolge Tief

    run_max_price = run_min_price = close[start_pos]
    run_max_pos = run_min_pos = start_pos
    ext_price, ext_pos = close[start_pos], start_pos

    for i in range(start_pos + 1, n):
        price = close[i]
        thr = atr_mult * atr.iloc[i]
        if np.isnan(thr):
            continue

        if direction == 0:
            if price > run_max_price:
                run_max_price, run_max_pos = price, i
            if price < run_min_price:
                run_min_price, run_min_pos = price, i
            if run_max_price - run_min_price >= thr:
                if run_max_pos < run_min_pos:
                    pivots.append((run_max_pos, "high", i))
                    direction, ext_price, ext_pos = -1, run_min_price, run_min_pos
                else:
                    pivots.append((run_min_pos, "low", i))
                    direction, ext_price, ext_pos = 1, run_max_price, run_max_pos
            continue

        if direction == 1:  # verfolge Hoch-Kandidat
            if price > ext_price:
                ext_price, ext_pos = price, i
            elif ext_price - price >= thr:
                pivots.append((ext_pos, "high", i))
                direction, ext_price, ext_pos = -1, price, i
        else:  # direction == -1, verfolge Tief-Kandidat
            if price < ext_price:
                ext_price, ext_pos = price, i
            elif price - ext_price >= thr:
                pivots.append((ext_pos, "low", i))
                direction, ext_price, ext_pos = 1, price, i

    # "idx" = Position des tatsaechlichen Extrems (fuer Struktur-/CV-Analyse).
    # "confirm_idx" = Position, an der der Pivot ERST ERKENNBAR wurde (Schwelle
    # gerissen) -- das ist der einzige Zeitpunkt, den ein Live-Handelssignal
    # verwenden darf, sonst Look-ahead-Bias (siehe research_ipda_pivot_timing_eurusd.py).
    out = pd.DataFrame(pivots, columns=["idx", "kind", "confirm_idx"]).drop_duplicates(subset="idx").sort_values("idx")
    out["date"] = df.index[out["idx"].to_numpy()]
    out["confirm_date"] = df.index[out["confirm_idx"].to_numpy()]
    out["price"] = df["Close"].to_numpy()[out["idx"].to_numpy()]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------
# 2. Monatsanfaenge (Handelstag-Index)
# --------------------------------------------------------------------------
def month_start_positions(index: pd.DatetimeIndex) -> np.ndarray:
    s = pd.Series(np.arange(len(index)), index=index)
    firsts = s.groupby([index.year, index.month]).head(1)
    return np.sort(firsts.to_numpy())


# --------------------------------------------------------------------------
# 3. Phasen-Zuordnung + Anreicherungs-Statistik
# --------------------------------------------------------------------------
def enrichment_score(pivot_idx: np.ndarray, anchors: np.ndarray, n_days: int, cycle_len: int, target_day: int, window: int) -> float:
    """Ordnet jeden Pivot dem naechstgelegenen VORHERIGEN Anker zu, berechnet
    die Phase (Tage seit Anker) und misst, wie stark sich Pivots im
    Toleranzfenster um `target_day` haeufen -- normiert gegen die unter
    Gleichverteilung erwartete Rate, sodass Werte > 1 = Anreicherung,
    Werte um 1 = kein Effekt, vergleichbar ueber verschiedene Zykluslaengen."""
    if len(anchors) == 0 or len(pivot_idx) == 0:
        return np.nan
    anchor_pos = np.searchsorted(anchors, pivot_idx, side="right") - 1
    valid = anchor_pos >= 0
    phase = pivot_idx[valid] - anchors[anchor_pos[valid]]
    in_cycle = phase < cycle_len
    phase = phase[in_cycle]
    if len(phase) == 0:
        return np.nan
    lo, hi = target_day - window, target_day + window
    hit_rate = np.mean((phase >= lo) & (phase <= hi))
    expected_rate = (min(hi, cycle_len - 1) - max(lo, 0) + 1) / cycle_len
    return hit_rate / expected_rate


def grid_scan(pivot_idx: np.ndarray, index: pd.DatetimeIndex, target_day_l20: int) -> pd.DataFrame:
    n_days = len(index)
    month_starts = month_start_positions(index)
    rows = []
    for cycle_len in CYCLE_LENGTHS:
        target_day = round(target_day_l20 * cycle_len / 20)
        for offset in OFFSET_RANGE:
            anchors = np.sort(np.clip(month_starts + offset, 0, n_days - 1))
            anchors = np.unique(anchors)
            score = enrichment_score(pivot_idx, anchors, n_days, cycle_len, target_day, WINDOW)
            rows.append({"cycle_len": cycle_len, "offset": offset, "target_day": target_day, "score": score})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 4. Permutationstest (zirkulaerer Shift, wie asian_range_breakout/randomization.py)
# --------------------------------------------------------------------------
def circular_shift(pivot_idx: np.ndarray, n_days: int, shift: int) -> np.ndarray:
    return np.sort((pivot_idx + shift) % n_days)


def run_permutation(pivot_idx: np.ndarray, index: pd.DatetimeIndex, target_day_l20: int, label: str, rng: np.random.Generator) -> tuple[pd.DataFrame, float, float]:
    observed = grid_scan(pivot_idx, index, target_day_l20)
    observed_best_row = observed.loc[observed["score"].idxmax()]
    observed_best = observed_best_row["score"]

    n_days = len(index)
    null_best = np.empty(N_PERM)
    null_per_cell = {(r.cycle_len, r.offset): [] for r in observed.itertuples()}
    for p in range(N_PERM):
        shift = int(rng.integers(1, n_days - 1))
        shifted = circular_shift(pivot_idx, n_days, shift)
        scan = grid_scan(shifted, index, target_day_l20)
        null_best[p] = scan["score"].max()
        for r in scan.itertuples():
            null_per_cell[(r.cycle_len, r.offset)].append(r.score)

    observed["p_cell"] = [
        np.mean(np.array(null_per_cell[(r.cycle_len, r.offset)]) >= r.score)
        for r in observed.itertuples()
    ]
    p_global = np.mean(null_best >= observed_best)

    print(f"\n=== {label}: bestes Raster-Ergebnis ===")
    print(observed_best_row)
    print(f"Global (mehrfachvergleichs-korrigiert ueber {len(observed)} Kombinationen) p = {p_global:.4f}")
    return observed.sort_values("score", ascending=False), observed_best, p_global


def main():
    print(f"Lade {PAIR} Daily ({START} - {END}) via Dukascopy (gecacht)...")
    df = fetch_timeframe(PAIR, "D1", START, END)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    n = len(df)
    split_i = int(n * IS_FRACTION)
    is_df, oos_df = df.iloc[:split_i], df.iloc[split_i:]
    print(f"Geladen: {n} Handelstage, {df.index[0].date()} - {df.index[-1].date()}")
    print(f"IS: {len(is_df)} Tage ({is_df.index[0].date()} - {is_df.index[-1].date()})")
    print(f"OOS: {len(oos_df)} Tage ({oos_df.index[0].date()} - {oos_df.index[-1].date()})")

    pivots = zigzag_pivots(is_df, ATR_MULT, ATR_PERIOD)
    spacing = np.diff(pivots["idx"].to_numpy())
    print(f"\nZigZag (ATR({ATR_PERIOD}) x {ATR_MULT}): {len(pivots)} Pivots im IS-Zeitraum")
    print(f"Median Pivot-Abstand: {np.median(spacing):.1f} Handelstage (Vergleich: Zyklus-Hypothese = ~20)")

    rng = np.random.default_rng(RANDOM_SEED)
    pivot_idx = pivots["idx"].to_numpy()
    for label, target in [("Tag 8", TARGET_DAYS_AT_L20["tag8"]), ("Tag 14", TARGET_DAYS_AT_L20["tag14"])]:
        run_permutation(pivot_idx, is_df.index, target, label, rng)


if __name__ == "__main__":
    main()
