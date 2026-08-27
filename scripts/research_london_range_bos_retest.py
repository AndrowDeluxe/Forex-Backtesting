"""London-Range Breakout->Retest->Fractal/CHOCH-Entry auf EUR/USD M5
(User-Vorgabe, 2026-08-12). Range = Hoch/Tief zwischen 06:00-07:00
Berlin-Zeit. Danach:

1. Erster Breakout: erste M5-Kerze NACH 07:00, deren CLOSE ausserhalb der
   Range liegt (>r_hi oder <r_lo) -- Richtung wird festgehalten.
2. Retest: erste nachfolgende Kerze, deren CLOSE wieder INNERHALB der Range
   liegt.
3. Entry (2026-08-12 geaendert -- ersetzt den fruehreren Range-Level-BOS mit
   Markt-Entry): eine RESTING STOP-ORDER, ausgeloest durch welchen der
   folgenden zwei Trigger zuerst tatsaechlich FUELLT (nicht: zuerst sucht):
   (a) Fractal-Trigger: erstes bestaetigtes 3-Bar-M5-Fractal GEGEN die
       Breakout-Richtung nach dem Retest (identische Konvention wie
       cls_practical/engine.py::_continuation_trigger), Stop-Order am
       eigenen Gegenextrem des Fractal-Pivots.
   (b) CHOCH-Trigger ("Change of Character"): Stop-Order direkt am eigenen
       Hoch/Tief des Retest-Bars selbst, ohne Fractal-Bestaetigung, sofort
       aktiv. ANNAHME (nicht explizit spezifiziert, hier dokumentiert): dies
       ist die einzige CHOCH-Lesart, die sich klar von (a) unterscheidet und
       ohne weitere Annahmen backtestbar ist.

Entry-Preis = Stop-Order-Level selbst (kein Slippage/Gap modelliert), plus
halber Spread (spread_bps=0.3, Projekt-Konvention).

SL: immer sl_atr_mult x ATR(14) auf M5 (Wilder, letzter VOLLSTAENDIG
geschlossener Bar vor Entry, kein Lookahead).

TP: drei Modi (tp_mode, 2026-08-12 um "rr"/"adr" erweitert nach Nutzerfrage,
ob feste 1:2/1:3-R-TPs bzw. ein ADR-basiertes TP schon getestet wurden):
- "atr" (Original-Sweep): tp_atr_mult x ATR(14) M5, UNABHAENGIG von SL
  (0.5-3.5 im Sweep).
- "rr": tp_rr x SL-Distanz (fester R-Multiple-TP, z.B. 1:2/1:3).
- "adr": tp_adr_mult x ADR(14) (Average Daily Range in Pips) -- gleicher
  Default-Multiplikator (0.35) wie asian_range_breakout/cls_settle.py's
  bereits etabliertes adr_mult, hier per compute_adr() wiederverwendet
  (Vortages-Durchschnitt, kein Lookahead).

Breakeven (2026-08-12, User-Vorgabe): sobald der Trade um be_trigger_r x
SL-Distanz im Plus steht (1:0.5 bis 1:1 im Sweep), wird der Stop auf den
Entry-Preis nachgezogen. be_trigger_r=None deaktiviert BE komplett.

Drei zusaetzliche Filter (2026-08-12, User-Vorgabe):
- entry_cutoff: Entry wird nur akzeptiert, wenn er VOR dieser Uhrzeit liegt
  (Default 11:00 Berlin) -- spaetere BOS-Signale werden verworfen.
- max_range_pips: Setup wird nur genommen, wenn die 06:00-07:00-Range
  schmaler als dieser Wert ist (Default 20 Pips) -- sehr breite Ranges
  deuten auf einen bereits volatilen/News-getriebenen Vormittag hin.
- VIX-Filter (asian_range_breakout/vix.py, ^VIX via yfinance): liegt der
  zuletzt bekannte VIX-Schluss ueber vix_threshold (Default 20), wird
  sl_atr_mult um vix_sl_boost (Default +0.5) erhoeht -- breiterer Stop in
  volatilen Marktphasen. "Zuletzt bekannt" = VORTAG-Schluss (per-Definition
  kein Lookahead, siehe _prior_day_vix_per_bar(): der heutige VIX-Schluss
  existiert erst nach US-Boersenschluss, lange nach dem Berliner Vormittag).

Cutoff fuer die Breakout->Retest->Entry-Kette selbst (unabhaengig vom
Entry-Cutoff-Filter oben): laeuft die Kette nicht bis zum Start der
NAECHSTEN Range durch, wird das Setup verworfen (analog zu
asian_range_breakout/cls_settle.py's Fensterlogik).

Backtest-Fenster: intraday_backtest_config.py (10 Jahre EUR/USD M5, 5 Jahre
In-Sample 2016-2021 zum Sweepen, 5 Jahre Out-of-Sample 2021-2026 fuer die
EINMALIGE Verifikation des besten In-Sample-Kandidaten -- nicht selbst
sweepen, sonst verbrennt der Holdout seinen Zweck."""

import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))

from asian_range_breakout.cls_settle import compute_adr  # noqa: E402
from asian_range_breakout.vix import fetch_vix_daily  # noqa: E402
from cls_practical.data import fetch_eurusd_entry_tf_berlin  # noqa: E402
from strategy.indicators import compute_atr  # noqa: E402

RANGE_START = "06:00"
RANGE_END = "07:00"
ATR_PERIOD = 14
SPREAD_BPS = 0.3
PIP_SIZE = 0.0001

CONFIRM_BUFFER_PIPS = 0.0  # siehe archivierte Option (b) im Chat-Verlauf: 2 Pips war klar negativ
CONFIRM_BUFFER = CONFIRM_BUFFER_PIPS * PIP_SIZE


def _minutes(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def _prior_day_vix_per_bar(index: pd.DatetimeIndex) -> np.ndarray:
    """VIX-Schlusskurs des zuletzt bekannten US-Handelstages fuer jeden Bar in
    `index` -- kein Lookahead: der VIX-Schluss eines Kalendertags existiert
    erst nach US-Boersenschluss (~22:00 Berlin), lange NACH dem Berliner
    Vormittag, in dem diese Strategie handelt. Deshalb wird der VIX-Wert erst
    ab dem naechsten Kalendertag als 'bekannt' behandelt (Shift +1 Tag), dann
    per ffill ueber Wochenenden/Feiertage auf jeden Bar-Tag gemappt (gleiche
    Shift-dann-ffill-Konvention wie compute_m30_atr/compute_adr in
    asian_range_breakout/cls_settle.py)."""
    idx_naive = index.tz_localize(None) if index.tz is not None else index
    start = (idx_naive.min() - pd.Timedelta(days=10)).date().isoformat()
    end = (idx_naive.max() + pd.Timedelta(days=2)).date().isoformat()
    vix = fetch_vix_daily(start, end)
    vix.index = vix.index + pd.Timedelta(days=1)  # ab wann der Wert bekannt ist
    daily_calendar = pd.date_range(vix.index.min(), idx_naive.max().normalize() + pd.Timedelta(days=1), freq="D")
    vix_daily = vix.reindex(daily_calendar).ffill()
    day_key = pd.DatetimeIndex(idx_naive.date)
    return vix_daily.reindex(day_key).to_numpy()


def simulate(
    df: pd.DataFrame,
    sl_atr_mult: float = 2.0,
    tp_mode: str = "atr",          # "atr" | "rr" | "adr"
    tp_atr_mult: float = 4.0,      # nur tp_mode="atr"
    tp_rr: float = 2.0,            # nur tp_mode="rr": TP = tp_rr x SL-Distanz
    tp_adr_mult: float = 0.35,     # nur tp_mode="adr": TP = tp_adr_mult x ADR(14) -- gleicher
                                    # Wert wie asian_range_breakout/cls_settle.py's adr_mult-Default
    adr_period: int = 14,
    be_trigger_r: float | None = None,
    entry_cutoff: str = "11:00",
    max_range_pips: float | None = 20.0,
    vix_threshold: float | None = 20.0,
    vix_sl_boost: float = 0.5,
) -> pd.DataFrame:
    if tp_mode not in ("atr", "rr", "adr"):
        raise ValueError(f"unknown tp_mode={tp_mode!r}, expected 'atr'/'rr'/'adr'")

    start_min, end_min = _minutes_of(RANGE_START), _minutes_of(RANGE_END)
    cutoff_min = _minutes_of(entry_cutoff)
    minutes = _minutes(df.index)
    in_window = (minutes >= start_min) & (minutes < end_min)

    atr = compute_atr(df, n=ATR_PERIOD).shift(1).to_numpy()  # kein Lookahead
    vix_per_bar = _prior_day_vix_per_bar(df.index) if vix_threshold is not None else None
    adr = compute_adr(df, n=adr_period) if tp_mode == "adr" else None  # bereits shift(1), kein Lookahead

    o, h, l, c = (df[col].to_numpy() for col in ("open", "high", "low", "close"))
    times = df.index
    n = len(df)
    half_spread = df["close"].mean() * SPREAD_BPS / 10_000 / 2
    max_range = max_range_pips * PIP_SIZE if max_range_pips is not None else None

    trades = []
    i = 0
    while i < n:
        while i < n and not in_window[i]:
            i += 1
        if i >= n:
            break
        window_start = i
        while i < n and in_window[i]:
            i += 1
        window_end = i  # exklusiv, Range gerade geschlossen
        if window_end >= n:
            break

        r_hi, r_lo = h[window_start:window_end].max(), l[window_start:window_end].min()
        range_width = r_hi - r_lo
        if range_width <= 0:
            continue

        j = window_end
        while j < n and not in_window[j]:
            j += 1
        cutoff = j  # exklusiv -- naechste Range-Bildung

        if max_range is not None and range_width > max_range:
            i = cutoff
            continue

        # Schritt 1: erster Breakout
        bo1_i, direction = None, 0
        k = window_end
        while k < cutoff:
            if c[k] > r_hi + CONFIRM_BUFFER:
                bo1_i, direction = k, 1
                break
            if c[k] < r_lo - CONFIRM_BUFFER:
                bo1_i, direction = k, -1
                break
            k += 1
        if bo1_i is None:
            i = cutoff
            continue

        # Schritt 2: Retest
        retest_i = None
        k = bo1_i + 1
        while k < cutoff:
            if direction == 1 and c[k] <= r_hi - CONFIRM_BUFFER and c[k] >= r_lo:
                retest_i = k
                break
            if direction == -1 and c[k] >= r_lo + CONFIRM_BUFFER and c[k] <= r_hi:
                retest_i = k
                break
            k += 1
        if retest_i is None:
            i = cutoff
            continue

        # Schritt 3 (2026-08-12, User-Vorgabe -- ersetzt den fruehreren
        # Range-Level-BOS): kein Markt-Entry mehr am naechsten Bar-Open nach
        # dem BOS, sondern eine RESTING STOP-ORDER, ausgeloest durch
        # WELCHER der beiden folgenden Trigger zuerst FUELLT (nicht: zuerst
        # sucht -- die tatsaechliche Fuell-Kerze entscheidet):
        #
        # (a) Fractal-Trigger: erstes bestaetigtes 3-Bar-M5-Fractal GEGEN die
        #     Breakout-Richtung nach dem Retest (identische Konvention wie
        #     cls_practical/engine.py::_continuation_trigger -- pivot bei j
        #     mit high[j]>high[j-1] und high[j]>high[j+1] fuer "high", bestae-
        #     tigt bei j+1, kein Lookahead). Stop-Order am eigenen
        #     Gegenextrem des Pivot-Bars (long: buy stop ueber dem Pivot-
        #     Hoch; short: sell stop unter dem Pivot-Tief).
        # (b) CHOCH-Trigger ("Change of Character"): eine Resting-Stop-Order
        #     direkt am eigenen Hoch/Tief des RETEST-Bars selbst -- keine
        #     Fractal-Bestaetigung noetig, sofort ab retest_i+1 aktiv. Das
        #     ist die schnellstmoegliche der beiden Auslesungen; der
        #     Fractal-Trigger dient als Alternative, falls dieses Level nie
        #     beruehrt wird, aber vorher ein echtes Pullback-Fractal entsteht.
        #
        # ANNAHME (nicht explizit spezifiziert, hier dokumentiert): "CHOCH"
        # wird als sofortige Order am Retest-Bar-Extrem interpretiert, nicht
        # als eigener, spaeter bestaetigter Struktur-Bruch -- die einzige
        # Lesart, die sich klar von der Fractal-Variante (a) unterscheidet
        # UND ohne weitere Annahmen backtestbar ist.
        fractal_kind = "low" if direction == 1 else "high"
        pivot_i, confirm_i = None, None
        j = max(retest_i, 1)
        while j < cutoff - 1:
            if j - 1 >= retest_i:
                if fractal_kind == "high" and h[j] > h[j - 1] and h[j] > h[j + 1]:
                    pivot_i, confirm_i = j, j + 1
                    break
                if fractal_kind == "low" and l[j] < l[j - 1] and l[j] < l[j + 1]:
                    pivot_i, confirm_i = j, j + 1
                    break
            j += 1

        candidates = []
        if pivot_i is not None:
            lvl = h[pivot_i] if direction == 1 else l[pivot_i]
            sl_ref = l[pivot_i] if direction == 1 else h[pivot_i]
            k = confirm_i
            while k < cutoff:
                if (direction == 1 and h[k] >= lvl) or (direction == -1 and l[k] <= lvl):
                    candidates.append((k, lvl, sl_ref, "fractal"))
                    break
                k += 1
        choch_lvl = h[retest_i] if direction == 1 else l[retest_i]
        choch_sl_ref = l[retest_i] if direction == 1 else h[retest_i]
        k = retest_i + 1
        while k < cutoff:
            if (direction == 1 and h[k] >= choch_lvl) or (direction == -1 and l[k] <= choch_lvl):
                candidates.append((k, choch_lvl, choch_sl_ref, "choch"))
                break
            k += 1

        if not candidates:
            i = cutoff
            continue
        candidates.sort(key=lambda x: x[0])  # fruehester tatsaechlicher Fill gewinnt
        entry_i, trigger_level, structure_sl_ref, trigger_kind = candidates[0]

        if entry_i >= n or np.isnan(atr[entry_i]) or atr[entry_i] <= 0:
            i = cutoff
            continue
        if minutes[entry_i] >= cutoff_min:
            i = cutoff
            continue

        entry_price = trigger_level + half_spread if direction == 1 else trigger_level - half_spread
        vix_at_entry = vix_per_bar[entry_i] if vix_per_bar is not None else np.nan
        high_vix = vix_threshold is not None and not np.isnan(vix_at_entry) and vix_at_entry > vix_threshold
        effective_sl_mult = sl_atr_mult + (vix_sl_boost if high_vix else 0.0)
        sl_dist = effective_sl_mult * atr[entry_i]

        if tp_mode == "rr":
            tp_dist = tp_rr * sl_dist
        elif tp_mode == "adr":
            if np.isnan(adr[entry_i]) or adr[entry_i] <= 0:
                i = cutoff
                continue
            tp_dist = tp_adr_mult * adr[entry_i]
        else:  # "atr"
            tp_dist = tp_atr_mult * atr[entry_i]

        sl = trigger_level - sl_dist if direction == 1 else trigger_level + sl_dist
        tp = trigger_level + tp_dist if direction == 1 else trigger_level - tp_dist

        exit_i, exit_price, exit_reason = None, None, None
        stop, be_moved = sl, False
        m = entry_i
        while m < n:
            if not be_moved and be_trigger_r is not None:
                favorable = (h[m] - entry_price) if direction == 1 else (entry_price - l[m])
                if favorable >= be_trigger_r * sl_dist:
                    stop, be_moved = entry_price, True

            hit_stop = (l[m] <= stop) if direction == 1 else (h[m] >= stop)
            hit_tp = (h[m] >= tp) if direction == 1 else (l[m] <= tp)
            if hit_stop:
                exit_price = stop - half_spread if direction == 1 else stop + half_spread
                exit_i, exit_reason = m, ("breakeven" if be_moved else "stop")
                break
            if hit_tp:
                exit_price = tp - half_spread if direction == 1 else tp + half_spread
                exit_i, exit_reason = m, "take_profit"
                break
            m += 1
        if exit_i is None:
            exit_price = c[n - 1] - half_spread if direction == 1 else c[n - 1] + half_spread
            exit_i, exit_reason = n - 1, "data_end"

        r_multiple = (exit_price - entry_price) / sl_dist if direction == 1 else (entry_price - exit_price) / sl_dist

        trades.append({
            "range_day": times[window_start].date().isoformat(),
            "range_width_pips": range_width / PIP_SIZE,
            "direction": "long" if direction == 1 else "short",
            "trigger_kind": trigger_kind,
            "entry_time": times[entry_i], "exit_time": times[exit_i],
            "vix_at_entry": vix_at_entry, "high_vix": high_vix,
            "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price,
            "sl_dist": sl_dist, "r_multiple": r_multiple, "exit_reason": exit_reason,
            "hold_bars": exit_i - entry_i,
        })
        i = max(exit_i + 1, cutoff)

    return pd.DataFrame(trades)


def summarize(trades: pd.DataFrame) -> dict:
    n = len(trades)
    if n == 0:
        return {"n_trades": 0, "win_rate": np.nan, "total_r": 0.0, "avg_r": np.nan}
    wins = trades[trades["r_multiple"] > 0]
    return {
        "n_trades": n,
        "win_rate": len(wins) / n,
        "total_r": trades["r_multiple"].sum(),
        "avg_r": trades["r_multiple"].mean(),
    }


def report(trades: pd.DataFrame, label: str) -> None:
    s = summarize(trades)
    print(f"\n=== {label}: {s['n_trades']} Trades ===")
    if s["n_trades"] == 0:
        return
    print(f"Win-Rate: {s['win_rate']*100:.1f}%")
    print(f"Summe R: {s['total_r']:+.2f}R, Durchschnitt: {s['avg_r']:+.2f}R/Trade")
    print(f"Exit-Gruende: {trades['exit_reason'].value_counts().to_dict()}")


ATR_MULT_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
BE_TRIGGER_GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def sweep_sl_tp(df_is: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    for sl_mult, tp_mult in product(ATR_MULT_GRID, ATR_MULT_GRID):
        trades = simulate(df_is, sl_atr_mult=sl_mult, tp_atr_mult=tp_mult, be_trigger_r=None)
        s = summarize(trades)
        rows.append({"sl_atr_mult": sl_mult, "tp_atr_mult": tp_mult, **s})
    print(f"SL x TP Sweep: {len(rows)} Kombinationen ({time.time()-t0:.1f}s)")
    return pd.DataFrame(rows)


def sweep_be(df_is: pd.DataFrame, sl_mult: float, **tp_kwargs) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    baseline = simulate(df_is, sl_atr_mult=sl_mult, be_trigger_r=None, **tp_kwargs)
    rows.append({"be_trigger_r": None, **summarize(baseline)})
    for be_r in BE_TRIGGER_GRID:
        trades = simulate(df_is, sl_atr_mult=sl_mult, be_trigger_r=be_r, **tp_kwargs)
        rows.append({"be_trigger_r": be_r, **summarize(trades)})
    print(f"BE-Sweep: {len(rows)} Varianten ({time.time()-t0:.1f}s)")
    return pd.DataFrame(rows)


# 2026-08-12, Nutzerfrage: feste 1:2/1:3-R-TPs und ein ADR-basiertes TP
# (0.35 x ADR(14), gleicher Multiplikator wie asian_range_breakout/
# cls_settle.py) waren im ATR-Grid-Sweep oben nicht explizit abgedeckt --
# eigener Vergleichs-Sweep ueber dieselbe SL-Grid.
TP_VARIANTS = [
    ("rr_1_2", "rr", {"tp_rr": 2.0}),
    ("rr_1_3", "rr", {"tp_rr": 3.0}),
    ("adr_0.35", "adr", {"tp_adr_mult": 0.35}),
]


def sweep_tp_modes(df_is: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    for sl_mult in ATR_MULT_GRID:
        for label, mode, kwargs in TP_VARIANTS:
            trades = simulate(df_is, sl_atr_mult=sl_mult, tp_mode=mode, be_trigger_r=None, **kwargs)
            s = summarize(trades)
            rows.append({"sl_atr_mult": sl_mult, "tp_variant": label, **s})
    print(f"TP-Modus-Vergleichs-Sweep: {len(rows)} Kombinationen ({time.time()-t0:.1f}s)")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import intraday_backtest_config as cfg

    t0 = time.time()
    print(f"Lade EUR/USD M5 {cfg.FULL_START.date()} .. {cfg.FULL_END.date()} (10 Jahre, gecacht nach erstem Lauf)...")
    df = fetch_eurusd_entry_tf_berlin("M5", cfg.FULL_START.isoformat(), cfg.FULL_END.isoformat())
    print(f"{len(df)} M5-Bars geladen ({time.time()-t0:.1f}s)")

    df_is = df.loc[cfg.IN_SAMPLE_START:cfg.IN_SAMPLE_END]
    df_oos = df.loc[cfg.OUT_SAMPLE_START:cfg.OUT_SAMPLE_END]
    print(f"In-Sample: {cfg.IN_SAMPLE_START.date()} .. {cfg.IN_SAMPLE_END.date()} ({len(df_is)} Bars)")
    print(f"Out-of-Sample: {cfg.OUT_SAMPLE_START.date()} .. {cfg.OUT_SAMPLE_END.date()} ({len(df_oos)} Bars)")

    out_dir = REPO_DIR / "london_range_bos_retest" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1a) SL x TP(ATR) Sweep, ohne BE, NUR auf In-Sample
    sweep_df = sweep_sl_tp(df_is)
    sweep_df.to_csv(out_dir / "sweep_sl_tp_in_sample.csv", index=False)
    best_atr = sweep_df.sort_values("total_r", ascending=False).iloc[0]
    print("\nBeste SL/TP(ATR)-Kombination (In-Sample, nach Summe R):")
    print(best_atr.to_string())
    best_atr_kwargs = {"tp_mode": "atr", "tp_atr_mult": best_atr["tp_atr_mult"]}

    # 1b) SL x TP-Modus-Vergleich (feste 1:2/1:3-R, ADR-basiert), NUR auf In-Sample
    tp_mode_df = sweep_tp_modes(df_is)
    tp_mode_df.to_csv(out_dir / "sweep_tp_modes_in_sample.csv", index=False)
    print("\nBeste Kombination je TP-Modus (In-Sample, nach Summe R):")
    best_per_variant = tp_mode_df.loc[tp_mode_df.groupby("tp_variant")["total_r"].idxmax()]
    print(best_per_variant.to_string(index=False))
    best_tp_mode_row = tp_mode_df.sort_values("total_r", ascending=False).iloc[0]
    variant_kwargs = dict(next(v for v in TP_VARIANTS if v[0] == best_tp_mode_row["tp_variant"])[2])
    best_tp_mode_kwargs = {"tp_mode": next(v for v in TP_VARIANTS if v[0] == best_tp_mode_row["tp_variant"])[1], **variant_kwargs}

    # Gesamt-bester Kandidat ueber ATR-Grid UND die drei neuen TP-Modi
    if best_atr["total_r"] >= best_tp_mode_row["total_r"]:
        best_sl, best_tp_kwargs, best_label = best_atr["sl_atr_mult"], best_atr_kwargs, f"tp_atr_mult={best_atr['tp_atr_mult']}"
    else:
        best_sl, best_tp_kwargs, best_label = best_tp_mode_row["sl_atr_mult"], best_tp_mode_kwargs, best_tp_mode_row["tp_variant"]
    print(f"\nGesamt-bester Kandidat: sl_atr_mult={best_sl}, {best_label}")

    # 2) BE-Sweep auf dem Gesamt-besten Kandidaten, NUR auf In-Sample
    be_df = sweep_be(df_is, best_sl, **best_tp_kwargs)
    be_df.to_csv(out_dir / "sweep_be_in_sample.csv", index=False)
    print("\nBE-Sweep auf Gesamt-bestem Kandidaten:")
    print(be_df.to_string(index=False))
    best_be = be_df.sort_values("total_r", ascending=False).iloc[0]

    # 3) EINMALIGE Verifikation des Gesamt-besten Kandidaten auf Out-of-Sample
    best_be_r = None if pd.isna(best_be["be_trigger_r"]) else best_be["be_trigger_r"]
    trades_oos = simulate(df_oos, sl_atr_mult=best_sl, be_trigger_r=best_be_r, **best_tp_kwargs)
    report(trades_oos, f"OUT-OF-SAMPLE-VERIFIKATION (sl={best_sl}, {best_label}, be={best_be_r})")
    trades_oos.to_csv(out_dir / "trades_oos_best_candidate.csv", index=False)

    print(f"\nGesamtlaufzeit: {time.time()-t0:.1f}s")
