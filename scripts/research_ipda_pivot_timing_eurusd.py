"""Phase-4-Ausbau der einzigen bisher robust bestaetigten IPDA-Teilthese:
ZigZag-Pivot-Abstaende in EUR/USD Daily sind signifikant regelmaessiger
(niedrigerer CV) als eine zufaellige Punktplatzierung, robust ueber 5 ATR-
Schwellenwerte (siehe knowledge/projects/ipda-zyklus-eurusd.md, Nachtrag
2026-08-25). Der Kalender-verankerte Tag-8/14/20-Zyklus UND der 8/14-EMA-
Cross als periodisches Signal sind beide widerlegt -- dieses Script prueft,
ob die reine ZEITLICHE Regelmaessigkeit der Pivots (unabhaengig von jedem
Kalenderanker) in eine profitable Handelsregel uebersetzt werden kann.

Regel: sobald seit der BESTAETIGUNG des letzten ZigZag-Pivots ein Zielfenster
von Handelstagen vergangen ist (User-Vorgabe: 20 +/- 2 Tage), wird GEGEN die
seit diesem Pivot laufende Bewegung eroeffnet (Fade/Reversal-Wette) -- SL
jenseits des seit dem Pivot erreichten Extrems (+ ATR-Puffer), TP als festes
R-Vielfaches, Fallback-Exit nach MAX_HOLD_DAYS.

Kritisch fuer Korrektheit: Entry nutzt AUSSCHLIESSLICH `confirm_idx` (der
Bar, an dem der Pivot erkennbar wurde), nie `idx` (die tatsaechliche Extrem-
Position, die im Voraus nicht bekannt sein kann) -- siehe Docstring von
zigzag_pivots() in research_ipda_cycle_daily_eurusd.py.

Vergleichs-Baseline OHNE Timing-Filter (sofortiger Fade-Entry direkt bei
jeder Pivot-Bestaetigung, kein Zeitfenster) trennt den Wert des TIMINGS vom
Wert der reinen "nach einem Pivot faden"-Idee -- Muster wie beim Execution-
Overlay-Test in knowledge/resources/fx-microstructure.md.

Chronologischer IS/OOS-Split wie in den vorherigen IPDA-Scripts (aeltere 70%
zum Sweepen, juengere 30% EINMAL zur Bestaetigung des besten IS-Kandidaten)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from combined_strategy.data import fetch_timeframe
from strategy.indicators import compute_atr
from scripts.research_ipda_cycle_daily_eurusd import zigzag_pivots

PAIR = "EURUSD"
START, END = "2003-01-01", "2026-08-24"
IS_FRACTION = 0.70

ATR_MULT_PIVOT = 2.0   # ZigZag-Schwelle (Ø-Abstand 18.0t im IS, naechster Wert an der 20-Tage-Vorgabe)
ATR_PERIOD = 14
TARGET_LO, TARGET_HI = 18, 22  # User-Vorgabe: 20 +/- 2 Handelstage
MAX_HOLD_DAYS = 25

SL_ATR_BUFFERS = [0.25, 0.5, 1.0]
TP_R_MULTIPLES = [1.5, 2.0, 3.0]


def simulate(df: pd.DataFrame, sl_atr_buf: float, tp_r: float, use_timing: bool) -> pd.DataFrame:
    """use_timing=False -> Baseline: Entry sofort bei jeder Pivot-Bestaetigung
    (kein Zeitfenster-Filter), sonst identische Trade-Mechanik."""
    lower = df.rename(columns=str.lower)
    atr = compute_atr(lower, n=ATR_PERIOD)
    high, low, close, open_ = (df[c].to_numpy() for c in ["High", "Low", "Close", "Open"])
    n = len(df)

    pivots = zigzag_pivots(df, ATR_MULT_PIVOT, ATR_PERIOD)
    confirms = pivots[["confirm_idx", "kind"]].sort_values("confirm_idx").reset_index(drop=True)

    trades = []
    blocked_until_i = -1  # solange i <= blocked_until_i: eine Position ist noch offen, kein neuer Entry
    last_confirm_i, last_kind = None, None
    running_extreme = None  # laufendes Extrem seit dem letzten bestaetigten Pivot

    confirm_ptr = 0
    n_confirms = len(confirms)

    for i in range(n):
        # neue Pivot-Bestaetigung(en) an diesem Bar uebernehmen
        while confirm_ptr < n_confirms and confirms.loc[confirm_ptr, "confirm_idx"] == i:
            last_confirm_i = i
            last_kind = confirms.loc[confirm_ptr, "kind"]
            running_extreme = close[i]  # Startpunkt fuer die neue Extrem-Verfolgung
            confirm_ptr += 1

        if last_kind == "low":
            running_extreme = max(running_extreme, high[i]) if running_extreme is not None else high[i]
        elif last_kind == "high":
            running_extreme = min(running_extreme, low[i]) if running_extreme is not None else low[i]

        if i <= blocked_until_i or last_confirm_i is None or np.isnan(atr.iloc[i]):
            continue

        days_since = i - last_confirm_i
        window_ok = True if not use_timing else (TARGET_LO <= days_since <= TARGET_HI)
        if not window_ok:
            continue

        # Fade-Richtung: letzter Pivot "high" (seither fallend) -> Long; "low" (seither steigend) -> Short
        direction = 1 if last_kind == "high" else -1
        if i + 1 >= n:
            continue
        entry_i = i + 1
        entry_price = open_[entry_i]
        buf = sl_atr_buf * atr.iloc[i]
        sl = running_extreme - buf if direction == 1 else running_extreme + buf
        risk = abs(entry_price - sl)
        if risk <= 0:
            continue
        tp = entry_price + direction * tp_r * risk

        exit_i, exit_price, r_mult = None, None, None
        for j in range(entry_i, min(entry_i + MAX_HOLD_DAYS, n)):
            if direction == 1:
                if low[j] <= sl:
                    exit_i, exit_price, r_mult = j, sl, -1.0
                    break
                if high[j] >= tp:
                    exit_i, exit_price, r_mult = j, tp, tp_r
                    break
            else:
                if high[j] >= sl:
                    exit_i, exit_price, r_mult = j, sl, -1.0
                    break
                if low[j] <= tp:
                    exit_i, exit_price, r_mult = j, tp, tp_r
                    break
        if exit_i is None:
            exit_i = min(entry_i + MAX_HOLD_DAYS - 1, n - 1)
            exit_price = close[exit_i]
            r_mult = direction * (exit_price - entry_price) / risk

        trades.append({
            "entry_date": df.index[entry_i], "exit_date": df.index[exit_i],
            "direction": direction, "days_since_pivot": days_since,
            "entry": entry_price, "sl": sl, "tp": tp, "exit": exit_price, "r": r_mult,
        })
        blocked_until_i = exit_i  # keine neue Position, solange diese noch offen ist
        last_confirm_i = None  # verhindert Mehrfach-Entry auf denselben Pivot; erst der naechste bestaetigte Pivot liefert ein neues Signal

    return pd.DataFrame(trades)


def summarize(trades: pd.DataFrame, label: str):
    if len(trades) == 0:
        print(f"{label}: 0 Trades")
        return
    total_r = trades["r"].sum()
    win_rate = (trades["r"] > 0).mean()
    gross_win = trades.loc[trades["r"] > 0, "r"].sum()
    gross_loss = -trades.loc[trades["r"] < 0, "r"].sum()
    pf = gross_win / gross_loss if gross_loss > 0 else np.nan
    print(f"{label}: n={len(trades)}, TotalR={total_r:+.2f}, Ø R={trades['r'].mean():+.3f}, "
          f"WinRate={win_rate*100:.1f}%, PF={pf:.2f}")


def main():
    print(f"Lade {PAIR} Daily ({START} - {END}) via Dukascopy (gecacht)...")
    df = fetch_timeframe(PAIR, "D1", START, END)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    split_i = int(len(df) * IS_FRACTION)
    is_df, oos_df = df.iloc[:split_i], df.iloc[split_i:]
    print(f"IS: {is_df.index[0].date()} - {is_df.index[-1].date()} ({len(is_df)} Tage)")
    print(f"OOS: {oos_df.index[0].date()} - {oos_df.index[-1].date()} ({len(oos_df)} Tage)\n")

    print("=== Baseline: Entry SOFORT bei jeder Pivot-Bestaetigung (kein Timing) -- IS ===")
    for buf in SL_ATR_BUFFERS:
        for tp in TP_R_MULTIPLES:
            trades = simulate(is_df, buf, tp, use_timing=False)
            summarize(trades, f"  SL_buf={buf}xATR, TP={tp}R")

    print(f"\n=== Getimt: Entry nur bei {TARGET_LO}-{TARGET_HI} Tagen seit Pivot-Bestaetigung -- IS ===")
    best = None
    for buf in SL_ATR_BUFFERS:
        for tp in TP_R_MULTIPLES:
            trades = simulate(is_df, buf, tp, use_timing=True)
            summarize(trades, f"  SL_buf={buf}xATR, TP={tp}R")
            if len(trades) >= 15:
                total_r = trades["r"].sum()
                if best is None or total_r > best[0]:
                    best = (total_r, buf, tp)

    if best is None:
        print("\nKein IS-Kandidat mit >=15 Trades gefunden -- Stichprobe zu klein fuer eine OOS-Bestaetigung.")
        return

    _, best_buf, best_tp = best
    print(f"\n=== Bester getimter IS-Kandidat: SL_buf={best_buf}xATR, TP={best_tp}R -- OOS-Bestaetigung (KEIN Retuning) ===")
    oos_trades = simulate(oos_df, best_buf, best_tp, use_timing=True)
    summarize(oos_trades, "  OOS")
    oos_baseline = simulate(oos_df, best_buf, best_tp, use_timing=False)
    summarize(oos_baseline, "  OOS (gleiche SL/TP, ohne Timing-Filter, zum Vergleich)")


if __name__ == "__main__":
    main()
