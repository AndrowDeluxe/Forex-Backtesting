"""ORB: SL/TP/Break-Even-Logik mit REALEN Kosten und dem heutigen
Ausfuehrungsmechanismus (ruhende Stop-Order) durchrechnen.

Nutzerauftrag 2026-09-19: "schaue ob wir mit den realen Daten und Kosten
nochmal an der SL, TP und BE Logik arbeiten sollten um das Edge profitabler zu
gestalten."

WAS HIER ANDERS IST als bei frueheren ORB-Backtests:
1. Entry = ruhende Stop-Order am Level (entry_fill_mode="level"), seit
   2026-09-17 live auf allen Bridges -- nicht mehr Markt bei Bar-Schluss.
2. Kosten = die je Instrument GEMESSENEN Broker-Spreads, nicht geschaetzt.
3. Einstiegs-Slippage = 0,45 bps statt 0,30 -- das ist der Mittelwert der
   fuenf ECHTEN Fills vom 17./18.09. (long +0,07..0,17 bps, short 0,88..1,03
   bps beim Durchbruch-Gap).
4. In-Sample/Out-of-Sample getrennt, damit ein Gitter-Optimum nicht als
   Ergebnis verkauft wird (Repo-Standard, siehe knowledge/areas/
   realkosten-und-ausfuehrungs-probe.md).

Ausgabe: ny_open_orb/results/exit_grid_<instrument>.csv + Konsolen-Report.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import filters, regime  # noqa: E402
from ny_open_orb.data import fetch_m5, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame, find_entries, simulate  # noqa: E402

START, END = "2019-01-01", "2026-09-18"
IS_END = "2022-12-31"          # In-Sample bis hier, danach Out-of-Sample

# Gemessene Broker-Spreads je Instrument (2026-09-13/14, scripts/
# measure_broker_spreads.py) -- Mittel ueber die drei Broker.
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}
ENTRY_SLIPPAGE_BPS = 0.45      # live gemessen 17./18.09. (5 Fills)
EXIT_SLIPPAGE_BPS = 0.30

# Gitter. Bewusst grob und gleichmaessig: ein feines Gitter findet zuverlaessig
# ein Optimum, das nur Rauschen ist.
STOP_ATR = [0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
TARGET_R = [None, 2.0, 3.0, 4.0, 5.0, 6.0]
PARTIAL_R = [None, 1.0, 1.5, 2.0, 2.5, 3.0]
BE_AFTER_PARTIAL = [True, False]
PARTIAL_FRACTION = 0.5


def load(instrument: str):
    m15 = pb._retry(lambda: fetch_m15(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    m5 = pb._retry(lambda: fetch_m5(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")
    if instrument == "NASDAQ":
        entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    else:
        long_entries = filters.filter_by_direction(all_entries, 1)
        bias = regime.ema_trend_bias(m15, frame["session"].unique())
        entries = filters.filter_by_category(long_entries, filters.values_at(long_entries, bias), (0.0,))
    return frame, entries


def metrics(trades: pd.DataFrame, label: str) -> dict:
    if trades.empty:
        return {f"{label}_trades": 0, f"{label}_avg_r": np.nan, f"{label}_pf": np.nan,
                f"{label}_win": np.nan, f"{label}_maxdd_r": np.nan, f"{label}_sum_r": np.nan}
    r = trades["r_multiple"]
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    equity = r.cumsum()
    return {
        f"{label}_trades": len(r),
        f"{label}_avg_r": r.mean(),
        f"{label}_pf": wins / losses if losses > 0 else np.inf,
        f"{label}_win": (r > 0).mean(),
        f"{label}_maxdd_r": (equity - equity.cummax()).min(),
        f"{label}_sum_r": r.sum(),
    }


def run_instrument(instrument: str) -> pd.DataFrame:
    frame, entries = load(instrument)
    rows = []
    for stop_atr in STOP_ATR:
        for target_r in TARGET_R:
            for partial_r in PARTIAL_R:
                for be in ([True, False] if partial_r is not None else [False]):
                    cfg = dict(
                        stop_atr_mult=stop_atr,
                        target_mode="r_multiple" if target_r is not None else None,
                        target_r_mult=target_r,
                        partial_exit_r=partial_r,
                        partial_exit_fraction=PARTIAL_FRACTION if partial_r is not None else 0.0,
                        move_stop_to_be_after_partial=be,
                    )
                    trades = simulate(
                        frame, entries,
                        spread_bps=SPREAD_BPS[instrument],
                        entry_slippage_bps=ENTRY_SLIPPAGE_BPS,
                        slippage_bps=EXIT_SLIPPAGE_BPS,
                        entry_fill_mode="level",
                        **cfg,
                    )
                    if trades.empty:
                        continue
                    et = pd.to_datetime(trades["entry_time"])
                    is_mask = et <= pd.Timestamp(IS_END, tz=et.dt.tz)
                    row = {"instrument": instrument, "stop_atr_mult": stop_atr,
                           "target_r_mult": target_r, "partial_exit_r": partial_r, "be": be}
                    row.update(metrics(trades, "all"))
                    row.update(metrics(trades[is_mask.values], "is"))
                    row.update(metrics(trades[~is_mask.values], "oos"))
                    # Jahres-Stabilitaet: in wie vielen Jahren ist Summe R > 0?
                    per_year = trades.groupby(et.dt.year)["r_multiple"].sum()
                    row["years_positive"] = int((per_year > 0).sum())
                    row["years_total"] = int(len(per_year))
                    rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    out_dir = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    current = {"SP500": (0.6, 4.0, 2.0, True), "US30": (0.6, 4.0, 2.0, True),
               "NASDAQ": (0.6, None, 1.5, True)}

    for instrument in ("SP500", "US30", "NASDAQ"):
        df = run_instrument(instrument)
        path = out_dir / f"exit_grid_{instrument}.csv"
        df.to_csv(path, index=False)
        print(f"\n{'='*78}\n{instrument}: {len(df)} Kombinationen -> {path}")

        s, t, p, b = current[instrument]
        cur = df[(df.stop_atr_mult == s) & (df.target_r_mult.isna() if t is None else df.target_r_mult == t)
                 & (df.partial_exit_r.isna() if p is None else df.partial_exit_r == p) & (df.be == b)]
        if not cur.empty:
            c = cur.iloc[0]
            print(f"HEUTE  stop {s} | TP {t} | Teil {p} | BE {b}: "
                  f"Ø R {c.all_avg_r:+.3f} | PF {c.all_pf:.2f} | Summe R {c.all_sum_r:+.0f} | "
                  f"OOS Ø R {c.oos_avg_r:+.3f} (PF {c.oos_pf:.2f}) | MaxDD {c.all_maxdd_r:.1f}R")

        # Kandidaten: nur was IS UND OOS positiv ist -- ein Gitter-Optimum, das
        # nur in einer Haelfte traegt, ist kein Kandidat.
        robust = df[(df.is_avg_r > 0) & (df.oos_avg_r > 0) & (df.all_trades > 200)]
        print(f"IS und OOS positiv: {len(robust)} von {len(df)}")
        for label, sort_col in (("bestes OOS Ø R", "oos_avg_r"), ("bestes Gesamt Ø R", "all_avg_r")):
            top = robust.sort_values(sort_col, ascending=False).head(5)
            print(f"\n  Top 5 nach {label}:")
            for _, r in top.iterrows():
                print(f"    stop {r.stop_atr_mult} | TP {r.target_r_mult} | Teil {r.partial_exit_r} | BE {int(r.be)} "
                      f"-> Ø R {r.all_avg_r:+.3f} (IS {r.is_avg_r:+.3f} / OOS {r.oos_avg_r:+.3f}) | "
                      f"PF {r.all_pf:.2f} | MaxDD {r.all_maxdd_r:.1f}R | Jahre+ {r.years_positive}/{r.years_total}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
