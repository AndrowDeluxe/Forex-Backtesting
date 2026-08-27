"""Phase-3-Plausibilitaetscheck fuer IPDA-Kandidat D: 20-Tage-Hoch/Tief
Liquidity-Sweep + Reversal ("Das Uhrwerk des Geldes"-PDF, Abschnitte
"Liquidity Pools", "Stop-Loss-Hunting" -- Beispiel im Dokument: "Ein IPDA-
Wendepunkt (z.B. der Preis erreicht das 20-Tage-Tief, um die dort liegende
Sell-Side-Liquiditaet abzugreifen)").

These operationalisiert als klassischer "Stop-Hunt": der Kurs durchbricht
das rollierende 20-Handelstage-Hoch/Tief NUR INTRABAR (Wick/Docht), schliesst
aber wieder INNERHALB der alten Range -- Liquiditaet wurde "abgegriffen",
aber der Ausbruch haelt nicht ("Fake-Out"). Erwartung laut Dokument: danach
Reversal (Preis dreht in die Gegenrichtung).

Gegenprobe (Kontrastgruppe): SAUBERER Breakout -- Kurs durchbricht das
20-Tage-Extrem UND schliesst auch dort/darueber (kein Fake-Out). Erwartung:
eher Fortsetzung (Momentum) statt Reversal -- falls die Sweep-These stimmt,
sollten sich Sweep- und Breakout-Ereignisse in ihrer Folge-Rendite deutlich
UNTERSCHEIDEN (nicht nur beide zufaellig sein).

Rollierendes Hoch/Tief nutzt `.shift(1)` (nur die 20 Tage VOR dem aktuellen
Bar), damit das aktuelle Bar nicht sein eigenes Vergleichslevel mitbestimmt
-- sonst waere "durchbricht das eigene Level" tautologisch.

Methodik wie in den vorherigen IPDA-Scripts: Permutationstest (zirkulaerer
Shift der Event-Tage, n=2000, "rotation"-Methode analog zu
asian_range_breakout/randomization.py), chronologischer IS/OOS-Split
(aeltere 70% / juengere 30%, keine Neukalibrierung auf OOS)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from combined_strategy.data import fetch_timeframe

PAIR = "EURUSD"
START, END = "2003-01-01", "2026-08-24"
IS_FRACTION = 0.70

LOOKBACK = 20  # Handelstage, rollierendes Hoch/Tief (User-Vorgabe: 20-Tage)
FORWARD_HORIZONS = [1, 3, 5, 10]
N_PERM = 2000
RANDOM_SEED = 42


def tag_events(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    roll_high = df["High"].shift(1).rolling(lookback).max()
    roll_low = df["Low"].shift(1).rolling(lookback).min()

    broke_high = df["High"] > roll_high
    broke_low = df["Low"] < roll_low
    closed_back_below = df["Close"] < roll_high
    closed_back_above = df["Close"] > roll_low

    out = pd.DataFrame(index=df.index)
    out["sweep_high"] = broke_high & closed_back_below       # Wick ueber altem Hoch, Close faellt zurueck -> Reversal-Erwartung: ABWAERTS
    out["sweep_low"] = broke_low & closed_back_above         # Wick unter altem Tief, Close steigt zurueck -> Reversal-Erwartung: AUFWAERTS
    out["breakout_high"] = broke_high & ~closed_back_below   # sauberer Ausbruch nach oben (haelt) -> Momentum-Erwartung: AUFWAERTS
    out["breakout_low"] = broke_low & ~closed_back_above     # sauberer Ausbruch nach unten (haelt) -> Momentum-Erwartung: ABWAERTS
    return out


def forward_returns(close: np.ndarray, event_idx: np.ndarray, horizon: int) -> np.ndarray:
    valid = event_idx[event_idx + horizon < len(close)]
    return np.log(close[valid + horizon] / close[valid])


def permutation_test(close: np.ndarray, event_idx: np.ndarray, horizon: int, rng: np.random.Generator, n_perm: int) -> tuple[float, float, float]:
    n_days = len(close)
    observed = forward_returns(close, event_idx, horizon).mean()
    null_means = np.empty(n_perm)
    for p in range(n_perm):
        shift = int(rng.integers(1, n_days - 1))
        shifted = np.sort((event_idx + shift) % n_days)
        null_means[p] = forward_returns(close, shifted, horizon).mean()
    p_two_sided = np.mean(np.abs(null_means) >= abs(observed))
    p_bearish = np.mean(null_means <= observed)   # H1: Preis faellt (Reversal nach Sweep-High / Momentum nach Breakout-Low)
    return observed, p_two_sided, p_bearish


def run_block(df: pd.DataFrame, label: str, rng: np.random.Generator):
    events = tag_events(df, LOOKBACK)
    close = df["Close"].to_numpy()
    print(f"\n=== {label} ({df.index[0].date()} - {df.index[-1].date()}) ===")
    for col, direction_note in [
        ("sweep_high", "erwartet ABWAERTS (Reversal)"),
        ("sweep_low", "erwartet AUFWAERTS (Reversal)"),
        ("breakout_high", "erwartet AUFWAERTS (Momentum)"),
        ("breakout_low", "erwartet ABWAERTS (Momentum)"),
    ]:
        idx = np.where(events[col].to_numpy())[0]
        n_events = len(idx)
        print(f"  {col} (n={n_events}, {direction_note}):")
        for h in FORWARD_HORIZONS:
            obs, p2, pb = permutation_test(close, idx, h, rng, N_PERM)
            print(f"    H={h:>2}d: mean logret={obs*10000:+6.1f} Pips-Aeq., p(2-seitig)={p2:.4f}, p(faellt)={pb:.4f}")


def main():
    print(f"Lade {PAIR} Daily ({START} - {END}) via Dukascopy (gecacht)...")
    df = fetch_timeframe(PAIR, "D1", START, END)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    split_i = int(len(df) * IS_FRACTION)
    is_df, oos_df = df.iloc[:split_i], df.iloc[split_i:]
    print(f"IS: {is_df.index[0].date()} - {is_df.index[-1].date()} ({len(is_df)} Tage)")
    print(f"OOS: {oos_df.index[0].date()} - {oos_df.index[-1].date()} ({len(oos_df)} Tage)")

    rng = np.random.default_rng(RANDOM_SEED)
    run_block(is_df, "IS-Screening", rng)
    run_block(oos_df, "OOS-Bestaetigung (keine Neukalibrierung)", rng)


if __name__ == "__main__":
    main()
